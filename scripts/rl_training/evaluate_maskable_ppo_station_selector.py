"""Evaluate a trained MaskablePPO Dundee station-selection checkpoint."""

from __future__ import annotations

import argparse
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

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.rl.scenarios import RLScenarioSampler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--checkpoint-path", type=Path, default=REPO_ROOT / "models" / "rl" / "maskable_ppo_station_selector.zip")
    parser.add_argument("--seed", type=int, default=2000)
    parser.add_argument("--duration-hours", type=int, default=1)
    parser.add_argument("--demand-level", default="normal", choices=["normal", "busy", "stress"])
    parser.add_argument("--max-steps", type=int, default=50)
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
    scenario = RLScenarioSampler(bundle=bundle).sample(
        seed=args.seed,
        split="validation",
        duration_hours=args.duration_hours,
        demand_level=args.demand_level,
    )
    print("MaskablePPO Dundee station selector evaluation setup")
    print(f"checkpoint_path: {args.checkpoint_path}")
    print(f"scenario_id: {scenario.scenario_id}")
    print(f"grid_advisory_mode: {args.grid_advisory_mode}")

    if args.dry_run:
        print("dry_run: no checkpoint loaded and no evaluation performed")
        return 0
    _require_evaluation_dependencies()
    if not args.checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {args.checkpoint_path}")

    from sb3_contrib import MaskablePPO
    from ev_core.rl.env import DundeeStationSelectionEnv

    env = DundeeStationSelectionEnv(
        repo_root=repo_root,
        scenario=scenario,
        bundle=bundle,
        grid_advisory_mode=args.grid_advisory_mode,
        grid_advisory_replay_dir=args.grid_replay_dir,
        grid_advisory_base_url=args.grid_advisory_base_url,
    )
    model = MaskablePPO.load(str(args.checkpoint_path))
    observation, _ = env.reset(seed=scenario.seed)
    rng = random.Random(scenario.seed)
    total_reward = 0.0
    steps = 0
    invalid_actions = 0
    missed = 0
    terminated = False

    while not terminated and steps < max(int(args.max_steps), 1):
        mask = env.action_masks()
        if not any(mask):
            action = 0
        else:
            action, _state = model.predict(observation, deterministic=True, action_masks=mask)
            action = int(action)
            if action < 0 or action >= len(mask) or not mask[action]:
                valid_actions = [index for index, allowed in enumerate(mask) if allowed]
                action = valid_actions[rng.randrange(len(valid_actions))]
        observation, reward, terminated, _truncated, info = env.step(action)
        total_reward += float(reward)
        invalid_actions += int(bool(info.get("invalid_action")))
        missed += int(bool(info.get("missed")))
        steps += 1

    print(
        json.dumps(
            {
                "scenario_id": scenario.scenario_id,
                "steps": steps,
                "total_reward": round(total_reward, 6),
                "invalid_actions": invalid_actions,
                "missed": missed,
            },
            indent=2,
        )
    )
    return 0


def _require_evaluation_dependencies() -> None:
    missing = [
        package_name
        for package_name in ("gymnasium", "stable_baselines3", "sb3_contrib")
        if importlib.util.find_spec(package_name) is None
    ]
    if missing:
        raise RuntimeError(
            "Missing RL evaluation packages: "
            + ", ".join(missing)
            + ". Install the EV-side requirements before evaluating a checkpoint."
        )


if __name__ == "__main__":
    raise SystemExit(main())
