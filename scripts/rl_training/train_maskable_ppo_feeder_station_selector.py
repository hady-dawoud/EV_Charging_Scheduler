"""Train MaskablePPO for DigitalTwin feeder public-EV station selection.

The default ``--dry-run`` path verifies data, imports, observation shape, action
masking, grid metric columns, and EV2Gym adapter availability without training.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
import time
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.rl_feeder.repository import DigitalTwinFeederRLRepository
from ev_core.rl_feeder.scenarios import FeederScenarioSampler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feeder-rl-data-dir", type=Path, default=_default_feeder_data_dir())
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "models" / "rl_feeder")
    parser.add_argument("--tensorboard-log", type=Path, default=REPO_ROOT / "outputs" / "rl_feeder" / "tensorboard")
    parser.add_argument("--grid-advisory-mode", default="disabled", choices=["disabled", "recorded", "http"])
    parser.add_argument("--grid-evaluation-mode", default="replay", choices=["replay", "surrogate", "ac_pf", "opf", "hybrid"])
    parser.add_argument("--grid-advisory-base-url", default="http://127.0.0.1:8091")
    parser.add_argument("--request-prior-sources", default="dundee,acn,digitaltwin")
    parser.add_argument(
        "--min-truth-level",
        default="any",
        choices=["exact_candidate_pf", "node_pf", "area_pf", "opf_proxy", "any"],
    )
    parser.add_argument("--exclude-adapter-proxy", action="store_true")
    parser.add_argument(
        "--require-replay-covered-area",
        action="store_true",
        help="sample scenarios only from feeder areas with replay rows that pass the truth filters",
    )
    parser.add_argument("--total-timesteps", type=int, default=10_000)
    parser.add_argument("--seed-start", type=int, default=3000)
    parser.add_argument("--scenario-count", type=int, default=4)
    parser.add_argument("--duration-hours", type=int, default=1)
    parser.add_argument(
        "--checkpoint-freq",
        type=int,
        default=100_000,
        help="save a checkpoint every N environment steps; set 0 to disable periodic checkpoints",
    )
    parser.add_argument("--resume-from", type=Path, default=None, help="resume from an existing MaskablePPO zip checkpoint")
    parser.add_argument(
        "--max-wall-clock-minutes",
        type=float,
        default=0.0,
        help="stop training after this many wall-clock minutes and save a graceful-stop checkpoint; 0 disables",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.feeder_rl_data_dir.resolve()
    repository = DigitalTwinFeederRLRepository(data_dir)
    action_frame = repository.load_action_catalog_frame()
    actions = repository.load_actions()
    priors = repository.load_request_priors()
    replay = repository.load_grid_replay()
    manifest = repository.load_manifest()
    quality_report = _load_json(data_dir / "quality_report.json")
    feature_stats = repository.load_feature_stats()
    covered_area_ids = _covered_area_ids(
        replay,
        min_truth_level=args.min_truth_level,
        exclude_adapter_proxy=args.exclude_adapter_proxy,
    )
    sampler_area_ids = covered_area_ids if args.require_replay_covered_area else None
    sampler = FeederScenarioSampler(actions=actions, allowed_area_ids=sampler_area_ids)
    request_sources = _split_sources(args.request_prior_sources)
    scenarios = [
        sampler.sample(
            seed=args.seed_start + index,
            split="train",
            duration_hours=args.duration_hours,
            request_prior_sources=request_sources,
            grid_evaluation_mode=args.grid_evaluation_mode,
        )
        for index in range(max(int(args.scenario_count), 1))
    ]

    print("MaskablePPO feeder public-EV station selector setup")
    print(f"feeder_rl_data_dir: {data_dir}")
    print(f"export_mode: {manifest.get('export_mode', 'unknown')}")
    print(f"area_count: {action_frame['secondary_area_id'].nunique()}")
    print(f"public_ev_action_count: {len(action_frame)}")
    print(f"request_prior_sources: {','.join(request_sources)}")
    print(f"request_prior_rows: {len(priors)}")
    print(f"grid_metric_columns: {','.join(_grid_metric_columns(replay))}")
    print(f"quality_report_available: {bool(quality_report)}")
    print(f"feature_stats_available: {bool(feature_stats)}")
    print(f"scenario_count: {len(scenarios)}")
    print(f"first_scenario_id: {scenarios[0].scenario_id}")
    print(f"grid_advisory_mode: {args.grid_advisory_mode}")
    print(f"evaluation_mode_used: {args.grid_evaluation_mode}")
    print(f"min_truth_level: {args.min_truth_level}")
    print(f"exclude_adapter_proxy: {args.exclude_adapter_proxy}")
    print(f"require_replay_covered_area: {args.require_replay_covered_area}")
    print(f"replay_covered_area_count: {len(covered_area_ids)}")
    print(f"training_sampler_area_count: {len(sampler.area_ids)}")
    print(f"checkpoint_freq: {args.checkpoint_freq}")
    print(f"resume_from: {args.resume_from}")
    print(f"max_wall_clock_minutes: {args.max_wall_clock_minutes}")
    print(f"ev2gym_config_available: {(data_dir / 'ev2gym_config' / 'feeder_ev2gym.yaml').exists()}")

    if args.dry_run:
        _print_dependency_status()
        if importlib.util.find_spec("gymnasium") is not None:
            env = _build_env(args=args, data_dir=data_dir, scenario=scenarios[0])
            observation, _info = env.reset(options={"scenario": scenarios[0]})
            print(f"observation_shape: {tuple(observation.shape)}")
            print(f"valid_action_count: {sum(env.action_masks())}")
        else:
            print("gymnasium_missing: install requirements before full training")
        print("dry_run: no training performed")
        return 0

    _require_training_dependencies()
    from sb3_contrib import MaskablePPO

    env = _build_training_env(args=args, data_dir=data_dir, scenarios=scenarios)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.tensorboard_log.mkdir(parents=True, exist_ok=True)
    if args.resume_from is not None:
        model = MaskablePPO.load(str(args.resume_from), env=env, tensorboard_log=str(args.tensorboard_log))
        print(f"loaded_checkpoint: {args.resume_from}")
        reset_num_timesteps = False
    else:
        model = MaskablePPO(
            "MlpPolicy",
            env,
            verbose=1,
            seed=scenarios[0].seed,
            tensorboard_log=str(args.tensorboard_log),
        )
        reset_num_timesteps = True
    callbacks = _build_callbacks(args=args)
    output_path = args.output_dir / "maskable_ppo_feeder_station_selector.zip"
    interrupted_path = args.output_dir / "maskable_ppo_feeder_station_selector_interrupted.zip"
    try:
        model.learn(
            total_timesteps=max(int(args.total_timesteps), 1),
            progress_bar=False,
            callback=callbacks,
            reset_num_timesteps=reset_num_timesteps,
        )
    except KeyboardInterrupt:
        model.save(str(interrupted_path))
        print(f"saved_interrupted_checkpoint: {interrupted_path}")
        raise
    output_path = args.output_dir / "maskable_ppo_feeder_station_selector.zip"
    model.save(str(output_path))
    print(f"saved_checkpoint: {output_path}")
    return 0


def _build_callbacks(*, args: argparse.Namespace):
    callbacks = []
    if int(args.checkpoint_freq or 0) > 0:
        from stable_baselines3.common.callbacks import CheckpointCallback

        checkpoint_dir = args.output_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        callbacks.append(
            CheckpointCallback(
                save_freq=max(int(args.checkpoint_freq), 1),
                save_path=str(checkpoint_dir),
                name_prefix="maskable_ppo_feeder_station_selector",
                save_replay_buffer=False,
                save_vecnormalize=False,
            )
        )
    if float(args.max_wall_clock_minutes or 0.0) > 0.0:
        from stable_baselines3.common.callbacks import BaseCallback

        class WallClockStopCallback(BaseCallback):
            def __init__(self, *, max_minutes: float, save_path: Path) -> None:
                super().__init__(verbose=1)
                self.max_seconds = float(max_minutes) * 60.0
                self.save_path = save_path
                self.started_at = time.monotonic()

            def _on_step(self) -> bool:
                if time.monotonic() - self.started_at < self.max_seconds:
                    return True
                self.model.save(str(self.save_path))
                print(f"saved_wall_clock_checkpoint: {self.save_path}")
                return False

        callbacks.append(
            WallClockStopCallback(
                max_minutes=float(args.max_wall_clock_minutes),
                save_path=args.output_dir / "maskable_ppo_feeder_station_selector_wall_clock_stop.zip",
            )
        )
    if not callbacks:
        return None
    if len(callbacks) == 1:
        return callbacks[0]
    from stable_baselines3.common.callbacks import CallbackList

    return CallbackList(callbacks)


def _build_env(*, args: argparse.Namespace, data_dir: Path, scenario: Any):
    from ev_core.rl_feeder.env import FeederStationSelectionEnv

    return FeederStationSelectionEnv(
        feeder_rl_data_dir=data_dir,
        scenario=scenario,
        grid_advisory_mode=args.grid_advisory_mode,
        grid_evaluation_mode=args.grid_evaluation_mode,
        grid_advisory_replay_dir=data_dir,
        grid_advisory_base_url=args.grid_advisory_base_url,
        min_truth_level=args.min_truth_level,
        exclude_adapter_proxy=args.exclude_adapter_proxy,
    )


def _build_training_env(*, args: argparse.Namespace, data_dir: Path, scenarios: list[Any]):
    from gymnasium import Wrapper

    class ScenarioCyclingEnv(Wrapper):
        def __init__(self) -> None:
            super().__init__(_build_env(args=args, data_dir=data_dir, scenario=scenarios[0]))
            self._scenario_index = 0

        def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
            scenario = scenarios[self._scenario_index % len(scenarios)]
            self._scenario_index += 1
            merged_options = dict(options or {})
            merged_options["scenario"] = scenario
            return self.env.reset(seed=seed or scenario.seed, options=merged_options)

        def action_masks(self):
            return self.env.action_masks()

    return ScenarioCyclingEnv()


def _grid_metric_columns(frame) -> list[str]:
    preferred = [
        "stress_score",
        "post_v_min_pu",
        "delta_v_min_pu",
        "post_max_line_loading_percent",
        "delta_max_line_loading_percent",
        "post_max_trafo_loading_percent",
        "delta_max_trafo_loading_percent",
        "opf_feasible",
        "opf_curtailment_kwh",
        "confidence_score",
    ]
    return [column for column in preferred if column in getattr(frame, "columns", [])]


def _split_sources(value: str) -> list[str]:
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _covered_area_ids(frame, *, min_truth_level: str, exclude_adapter_proxy: bool) -> list[str]:
    if frame is None or getattr(frame, "empty", True) or "secondary_area_id" not in frame.columns:
        return []
    result = frame.copy()
    if exclude_adapter_proxy and "physical_truth_level" in result.columns:
        result = result[result["physical_truth_level"].astype(str) != "adapter_proxy"].copy()
    if min_truth_level and min_truth_level != "any" and "physical_truth_level" in result.columns:
        min_rank = _truth_rank(min_truth_level)
        result = result[result["physical_truth_level"].astype(str).map(_truth_rank) >= min_rank].copy()
    return sorted(str(value) for value in result["secondary_area_id"].dropna().unique())


def _truth_rank(value: str) -> int:
    return {
        "unknown": 0,
        "adapter_proxy": 1,
        "opf_proxy": 2,
        "area_pf": 3,
        "node_pf": 4,
        "exact_candidate_pf": 5,
    }.get(str(value or "unknown"), 0)


def _print_dependency_status() -> None:
    for package_name in ("gymnasium", "stable_baselines3", "sb3_contrib", "tensorboard", "torch"):
        print(f"{package_name}: {bool(importlib.util.find_spec(package_name))}")
    if importlib.util.find_spec("torch") is not None:
        try:
            import torch

            print(f"torch_version: {torch.__version__}")
            print(f"torch_cuda_available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"torch_cuda_device_count: {torch.cuda.device_count()}")
                print(f"torch_cuda_device_name: {torch.cuda.get_device_name(0)}")
        except Exception as exc:
            print(f"torch_cuda_status_error: {exc}")


def _require_training_dependencies() -> None:
    missing = [
        package_name
        for package_name in ("gymnasium", "stable_baselines3", "sb3_contrib", "torch")
        if importlib.util.find_spec(package_name) is None
    ]
    if missing:
        raise RuntimeError(
            "Missing feeder RL training packages in this Python environment: "
            + ", ".join(missing)
            + ". Install them inside the active EV-side virtual environment before training."
        )


def _default_feeder_data_dir() -> Path:
    for parent in [REPO_ROOT, *REPO_ROOT.parents]:
        if parent.name == "DigitalTwin.2.0":
            return parent / "outputs" / "evside_feeder_rl"
    return REPO_ROOT / "outputs" / "evside_feeder_rl"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
