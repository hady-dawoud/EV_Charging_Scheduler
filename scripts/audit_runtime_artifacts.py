"""Audit runtime model and data artifacts required by optional RL/forecast paths."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ArtifactCheck:
    label: str
    alternatives: tuple[Path, ...]

    def present_path(self, repo_root: Path) -> Path | None:
        for relative_path in self.alternatives:
            candidate = repo_root / relative_path
            if candidate.exists():
                return relative_path
        return None


EXPECTED_ARTIFACTS: tuple[ArtifactCheck, ...] = (
    ArtifactCheck("models/rl/maskable_ppo_station_selector.zip", (Path("models/rl/maskable_ppo_station_selector.zip"),)),
    ArtifactCheck(
        "models/rl_feeder/maskable_ppo_feeder_station_selector.zip",
        (Path("models/rl_feeder/maskable_ppo_feeder_station_selector.zip"),),
    ),
    ArtifactCheck(
        "models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip",
        (Path("models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip"),),
    ),
    ArtifactCheck(
        "models/forecasting/load_kw_30min/lstm_huber_load_kw_30min.keras",
        (Path("models/forecasting/load_kw_30min/lstm_huber_load_kw_30min.keras"),),
    ),
    ArtifactCheck(
        "models/forecasting/load_kw_30min/load_kw_30min_feature_scaler.joblib",
        (Path("models/forecasting/load_kw_30min/load_kw_30min_feature_scaler.joblib"),),
    ),
    ArtifactCheck(
        "models/forecasting/load_kw_30min/load_kw_30min_target_scaler.joblib",
        (Path("models/forecasting/load_kw_30min/load_kw_30min_target_scaler.joblib"),),
    ),
    ArtifactCheck(
        "models/forecasting/load_kw_30min/load_kw_30min_training_metadata.json",
        (Path("models/forecasting/load_kw_30min/load_kw_30min_training_metadata.json"),),
    ),
    ArtifactCheck(
        "data/processed/evside_feeder_rl/manifest.json",
        (Path("data/processed/evside_feeder_rl/manifest.json"),),
    ),
    ArtifactCheck(
        "data/processed/evside_feeder_rl/feature_stats.json",
        (Path("data/processed/evside_feeder_rl/feature_stats.json"),),
    ),
    ArtifactCheck(
        "data/processed/evside_feeder_rl/feeder_ev_action_catalog.csv or .parquet",
        (
            Path("data/processed/evside_feeder_rl/feeder_ev_action_catalog.csv"),
            Path("data/processed/evside_feeder_rl/feeder_ev_action_catalog.parquet"),
        ),
    ),
    ArtifactCheck(
        "data/processed/evside_feeder_rl/feeder_request_priors.csv or .parquet",
        (
            Path("data/processed/evside_feeder_rl/feeder_request_priors.csv"),
            Path("data/processed/evside_feeder_rl/feeder_request_priors.parquet"),
        ),
    ),
    ArtifactCheck(
        "data/processed/evside_feeder_rl/feeder_grid_advisory_replay.csv or .parquet",
        (
            Path("data/processed/evside_feeder_rl/feeder_grid_advisory_replay.csv"),
            Path("data/processed/evside_feeder_rl/feeder_grid_advisory_replay.parquet"),
        ),
    ),
)


def audit(repo_root: Path) -> tuple[list[ArtifactCheck], list[ArtifactCheck]]:
    present: list[ArtifactCheck] = []
    missing: list[ArtifactCheck] = []
    for check in EXPECTED_ARTIFACTS:
        if check.present_path(repo_root) is None:
            missing.append(check)
        else:
            present.append(check)
    return present, missing


def render_report(repo_root: Path) -> str:
    present, missing = audit(repo_root)
    lines = [
        "Runtime artifact audit",
        f"repo_root: {repo_root}",
        "",
    ]
    for check in EXPECTED_ARTIFACTS:
        found = check.present_path(repo_root)
        if found is None:
            lines.append(f"MISSING  {check.label}")
        else:
            lines.append(f"PRESENT  {found.as_posix()}")
    lines.extend(
        [
            "",
            f"present: {len(present)}",
            f"missing: {len(missing)}",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true", help="exit with status 1 if any artifact is missing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    print(render_report(repo_root))
    _present, missing = audit(repo_root)
    return 1 if args.strict and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
