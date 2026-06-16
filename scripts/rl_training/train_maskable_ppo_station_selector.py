"""Train MaskablePPO for Dundee station selection.

The default CLI supports ``--dry-run`` so setup can be verified without starting
training or requiring heavyweight RL packages in the current interpreter.
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.rl.scenarios import RLScenarioSampler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "models" / "rl")
    parser.add_argument("--tensorboard-log", type=Path, default=REPO_ROOT / "outputs" / "rl" / "tensorboard")
    parser.add_argument("--total-timesteps", type=int, default=10_000)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--scenario-count", type=int, default=4)
    parser.add_argument("--duration-hours", type=int, default=1)
    parser.add_argument("--demand-level", default="normal", choices=["normal", "busy", "stress"])
    parser.add_argument("--routing-provider-name", default="simple_distance", choices=["simple_distance", "osmnx"])
    parser.add_argument("--grid-advisory-mode", default="disabled", choices=["disabled", "recorded", "http"])
    parser.add_argument("--grid-replay-dir", type=Path, default=None)
    parser.add_argument("--grid-advisory-base-url", default="http://127.0.0.1:8091")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    repository = DundeeSimulationRepository(repo_root)
    bundle = repository.load_bundle()
    sampler = RLScenarioSampler(bundle=bundle, routing_provider_name=args.routing_provider_name)
    scenarios = [
        sampler.sample(
            seed=args.seed_start + index,
            split="train",
            duration_hours=args.duration_hours,
            demand_level=args.demand_level,
        )
        for index in range(max(int(args.scenario_count), 1))
    ]

    print("MaskablePPO Dundee station selector setup")
    print(f"repo_root: {repo_root}")
    print(f"station_count: {len(bundle.stations)}")
    print(f"scenario_count: {len(scenarios)}")
    print(f"first_scenario_id: {scenarios[0].scenario_id}")
    print(f"grid_advisory_mode: {args.grid_advisory_mode}")

    if args.dry_run:
        _print_dependency_status()
        if importlib.util.find_spec("gymnasium") is not None:
            env = _build_env(args=args, repo_root=repo_root, scenario=scenarios[0], bundle=bundle)
            observation, info = env.reset(seed=scenarios[0].seed)
            print(f"observation_shape: {observation.shape}")
            print(f"valid_action_count: {sum(env.action_masks())}")
            print(f"info_keys: {sorted(info.keys())}")
        else:
            print("gymnasium_missing: install requirements before full training")
        print("dry_run: no training performed")
        return 0

    _require_training_dependencies()
    from sb3_contrib import MaskablePPO

    env = _build_training_env(args=args, repo_root=repo_root, scenarios=scenarios, bundle=bundle)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.tensorboard_log.mkdir(parents=True, exist_ok=True)
    model = MaskablePPO(
        "MlpPolicy",
        env,
        verbose=1,
        seed=scenarios[0].seed,
        tensorboard_log=str(args.tensorboard_log),
    )
    model.learn(total_timesteps=max(int(args.total_timesteps), 1), progress_bar=False)
    output_path = args.output_dir / "maskable_ppo_station_selector.zip"
    model.save(str(output_path))
    print(f"saved_checkpoint: {output_path}")
    return 0


def _build_env(*, args: argparse.Namespace, repo_root: Path, scenario: Any, bundle: Any):
    from ev_core.rl.env import DundeeStationSelectionEnv

    return DundeeStationSelectionEnv(
        repo_root=repo_root,
        scenario=scenario,
        bundle=bundle,
        grid_advisory_mode=args.grid_advisory_mode,
        grid_advisory_replay_dir=args.grid_replay_dir,
        grid_advisory_base_url=args.grid_advisory_base_url,
    )


def _build_training_env(*, args: argparse.Namespace, repo_root: Path, scenarios: list[Any], bundle: Any):
    from gymnasium import Wrapper

    class ScenarioCyclingEnv(Wrapper):
        def __init__(self) -> None:
            super().__init__(_build_env(args=args, repo_root=repo_root, scenario=scenarios[0], bundle=bundle))
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


def _print_dependency_status() -> None:
    for package_name in ("gymnasium", "stable_baselines3", "sb3_contrib", "tensorboard"):
        print(f"{package_name}: {bool(importlib.util.find_spec(package_name))}")


def _require_training_dependencies() -> None:
    missing = [
        package_name
        for package_name in ("gymnasium", "stable_baselines3", "sb3_contrib")
        if importlib.util.find_spec(package_name) is None
    ]
    if missing:
        raise RuntimeError(
            "Missing RL training packages: "
            + ", ".join(missing)
            + ". Install the EV-side requirements before running full training."
        )


if __name__ == "__main__":
    raise SystemExit(main())
