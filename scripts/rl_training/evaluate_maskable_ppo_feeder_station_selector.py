"""Evaluate a trained MaskablePPO feeder public-EV station-selector checkpoint."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import random
import sys


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
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        default=REPO_ROOT / "models" / "rl_feeder" / "maskable_ppo_feeder_station_selector.zip",
    )
    parser.add_argument("--seed", type=int, default=4000)
    parser.add_argument("--duration-hours", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--grid-advisory-mode", default="disabled", choices=["disabled", "recorded", "http"])
    parser.add_argument("--grid-evaluation-mode", default="replay", choices=["replay", "surrogate", "ac_pf", "opf", "hybrid"])
    parser.add_argument("--grid-advisory-base-url", default="http://127.0.0.1:8091")
    parser.add_argument("--policy", default="checkpoint", choices=["checkpoint", "random", "weighted"])
    parser.add_argument(
        "--min-truth-level",
        default="any",
        choices=["exact_candidate_pf", "node_pf", "area_pf", "opf_proxy", "any"],
    )
    parser.add_argument("--exclude-adapter-proxy", action="store_true")
    parser.add_argument(
        "--require-replay-covered-area",
        action="store_true",
        help="sample the validation scenario only from feeder areas with replay rows that pass the truth filters",
    )
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-csv", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.feeder_rl_data_dir.resolve()
    repository = DigitalTwinFeederRLRepository(data_dir)
    actions = repository.load_actions()
    replay = repository.load_grid_replay()
    covered_area_ids = _covered_area_ids(
        replay,
        min_truth_level=args.min_truth_level,
        exclude_adapter_proxy=args.exclude_adapter_proxy,
    )
    sampler_area_ids = covered_area_ids if args.require_replay_covered_area else None
    sampler = FeederScenarioSampler(actions=actions, allowed_area_ids=sampler_area_ids)
    scenario = sampler.sample(
        seed=args.seed,
        split="validation",
        duration_hours=args.duration_hours,
        grid_evaluation_mode=args.grid_evaluation_mode,
    )
    print("MaskablePPO feeder public-EV station selector evaluation setup")
    print(f"feeder_rl_data_dir: {data_dir}")
    print(f"checkpoint_path: {args.checkpoint_path}")
    print(f"public_ev_action_count: {len(actions)}")
    print(f"scenario_id: {scenario.scenario_id}")
    print(f"grid_advisory_mode: {args.grid_advisory_mode}")
    print(f"evaluation_mode_used: {args.grid_evaluation_mode}")
    print(f"policy: {args.policy}")
    print(f"min_truth_level: {args.min_truth_level}")
    print(f"exclude_adapter_proxy: {args.exclude_adapter_proxy}")
    print(f"require_replay_covered_area: {args.require_replay_covered_area}")
    print(f"replay_covered_area_count: {len(covered_area_ids)}")
    print(f"evaluation_sampler_area_count: {len(sampler.area_ids)}")

    if args.dry_run:
        print("dry_run: no checkpoint loaded and no evaluation performed")
        return 0

    _require_runtime_dependencies(policy=args.policy)
    if args.policy == "checkpoint" and not args.checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint_path}")

    from ev_core.rl_feeder.env import FeederStationSelectionEnv

    env = FeederStationSelectionEnv(
        feeder_rl_data_dir=data_dir,
        scenario=scenario,
        grid_advisory_mode=args.grid_advisory_mode,
        grid_evaluation_mode=args.grid_evaluation_mode,
        grid_advisory_replay_dir=data_dir,
        grid_advisory_base_url=args.grid_advisory_base_url,
        min_truth_level=args.min_truth_level,
        exclude_adapter_proxy=args.exclude_adapter_proxy,
    )
    model = _load_model(args) if args.policy == "checkpoint" else None
    observation, _ = env.reset(options={"scenario": scenario})
    rng = random.Random(scenario.seed)
    metrics = {
        "scenario_id": scenario.scenario_id,
        "policy": args.policy,
        "steps": 0,
        "total_reward": 0.0,
        "mean_reward": 0.0,
        "missed_requests": 0,
        "invalid_actions": 0,
        "fallback_actions": 0,
        "average_stress_score": 0.0,
        "max_stress_score": 0.0,
        "voltage_violation_count": 0,
        "line_overload_count": 0,
        "trafo_overload_count": 0,
        "opf_infeasible_count": 0,
        "mean_curtailment_required_kw": 0.0,
        "mean_feasible_energy_kwh": 0.0,
        "grid_evaluation_mode": args.grid_evaluation_mode,
        "truth_level_counts": {},
    }
    stress_values: list[float] = []
    curtailment_values: list[float] = []
    feasible_energy_values: list[float] = []
    terminated = False

    while not terminated and metrics["steps"] < max(int(args.max_steps), 1):
        mask = env.action_masks()
        if not any(mask):
            action = 0
        else:
            action, used_fallback = _select_action(
                args=args,
                env=env,
                model=model,
                observation=observation,
                mask=mask,
                rng=rng,
            )
            metrics["fallback_actions"] += int(used_fallback)
        observation, reward, terminated, _truncated, info = env.step(action)
        advisory = info.get("selected_grid_advisory") or {}
        metrics["steps"] += 1
        metrics["total_reward"] += float(reward)
        metrics["invalid_actions"] += int(bool(info.get("invalid_action")))
        metrics["missed_requests"] += int(bool(info.get("missed")))
        if advisory:
            stress_values.append(float(advisory.get("stress_score") or 0.0))
            curtailment_values.append(float(advisory.get("curtailment_required_kw") or 0.0))
            feasible_energy_values.append(float(advisory.get("feasible_energy_kwh") or 0.0))
            metrics["voltage_violation_count"] += int(advisory.get("voltage_violation_count") or 0)
            metrics["line_overload_count"] += int(advisory.get("line_overload_count") or 0)
            metrics["trafo_overload_count"] += int(advisory.get("trafo_overload_count") or 0)
            metrics["opf_infeasible_count"] += int(not bool(advisory.get("opf_feasible", True)))
            truth_level = str(advisory.get("physical_truth_level") or "unknown")
            metrics["truth_level_counts"][truth_level] = int(metrics["truth_level_counts"].get(truth_level, 0)) + 1

    if stress_values:
        metrics["average_stress_score"] = sum(stress_values) / len(stress_values)
        metrics["max_stress_score"] = max(stress_values)
    if curtailment_values:
        metrics["mean_curtailment_required_kw"] = sum(curtailment_values) / len(curtailment_values)
    if feasible_energy_values:
        metrics["mean_feasible_energy_kwh"] = sum(feasible_energy_values) / len(feasible_energy_values)
    if metrics["steps"]:
        metrics["mean_reward"] = metrics["total_reward"] / metrics["steps"]
    metrics["total_reward"] = round(float(metrics["total_reward"]), 6)
    metrics["mean_reward"] = round(float(metrics["mean_reward"]), 6)
    metrics["average_stress_score"] = round(float(metrics["average_stress_score"]), 6)
    metrics["max_stress_score"] = round(float(metrics["max_stress_score"]), 6)
    metrics["mean_curtailment_required_kw"] = round(float(metrics["mean_curtailment_required_kw"]), 6)
    metrics["mean_feasible_energy_kwh"] = round(float(metrics["mean_feasible_energy_kwh"]), 6)
    _write_outputs(metrics, output_json=args.output_json, output_csv=args.output_csv)
    print(json.dumps(metrics, indent=2))
    return 0


def _select_action(*, args: argparse.Namespace, env, model, observation, mask: list[bool], rng: random.Random) -> tuple[int, bool]:
    valid_actions = [index for index, allowed in enumerate(mask) if allowed]
    if args.policy == "random":
        return valid_actions[rng.randrange(len(valid_actions))], False
    if args.policy == "weighted":
        return _select_weighted_action(env=env, valid_actions=valid_actions), False

    action, _state = model.predict(observation, deterministic=True, action_masks=mask)
    action = int(action)
    if action < 0 or action >= len(mask) or not mask[action]:
        return valid_actions[rng.randrange(len(valid_actions))], True
    return action, False


def _select_weighted_action(*, env, valid_actions: list[int]) -> int:
    request = env.current_request
    if request is None:
        return valid_actions[0]
    scores: list[tuple[float, int]] = []
    for action_index in valid_actions:
        action = env.actions[action_index]
        advisory = env.current_grid_advisories.get(action.station_id)
        reward = env.reward_model.compute(
            selected_action=action,
            request=request,
            grid_advisory=advisory,
        ).total
        scores.append((float(reward), action_index))
    return max(scores)[1]


def _load_model(args: argparse.Namespace):
    from sb3_contrib import MaskablePPO

    return MaskablePPO.load(str(args.checkpoint_path))


def _require_runtime_dependencies(*, policy: str) -> None:
    required = ["gymnasium"]
    if policy == "checkpoint":
        required.extend(["stable_baselines3", "sb3_contrib", "torch"])
    missing = [package_name for package_name in required if importlib.util.find_spec(package_name) is None]
    if missing:
        raise RuntimeError(
            "Missing feeder RL evaluation packages in this Python environment: "
            + ", ".join(missing)
            + ". Install them inside the active EV-side virtual environment before evaluating."
        )


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


def _write_outputs(metrics: dict, *, output_json: Path | None, output_csv: Path | None) -> None:
    if output_json is not None:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    if output_csv is not None:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        exists = output_csv.exists()
        with output_csv.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(metrics))
            if not exists:
                writer.writeheader()
            writer.writerow(metrics)


def _default_feeder_data_dir() -> Path:
    for parent in [REPO_ROOT, *REPO_ROOT.parents]:
        if parent.name == "DigitalTwin.2.0":
            return parent / "outputs" / "evside_feeder_rl"
    return REPO_ROOT / "outputs" / "evside_feeder_rl"


if __name__ == "__main__":
    raise SystemExit(main())
