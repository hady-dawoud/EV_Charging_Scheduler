"""Check artifacts required for strict feeder RL deployment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_ARTIFACTS = (
    ("data/processed/evside_feeder_rl/manifest.json", "json"),
    ("data/processed/evside_feeder_rl/feature_stats.json", "json"),
    (
        "data/processed/evside_feeder_rl/"
        "feeder_ev_action_catalog.parquet",
        "parquet",
    ),
    (
        "data/processed/evside_feeder_rl/"
        "feeder_request_priors.parquet",
        "parquet",
    ),
    (
        "data/processed/evside_feeder_rl/"
        "feeder_grid_advisory_replay.parquet",
        "parquet",
    ),
    (
        "models/rl_feeder_final/"
        "maskable_ppo_feeder_station_selector.zip",
        "checkpoint",
    ),
)


def check_artifacts(
    repo_root: str | Path = REPO_ROOT,
    *,
    check_parquet: bool = False,
) -> dict[str, Any]:
    """Return a JSON-serializable strict deployment artifact report."""

    root = Path(repo_root).resolve()
    artifacts = [
        _check_artifact(
            root,
            relative_path=relative_path,
            kind=kind,
            check_parquet=check_parquet,
        )
        for relative_path, kind in REQUIRED_ARTIFACTS
    ]
    missing = sum(item["status"] == "missing" for item in artifacts)
    invalid = sum(item["status"] == "invalid" for item in artifacts)
    present = sum(item["exists"] for item in artifacts)
    parquet_checked = sum(
        item["kind"] == "parquet" and item["status"] == "valid"
        for item in artifacts
        if check_parquet
    )
    return {
        "passed": missing == 0 and invalid == 0,
        "check_parquet": bool(check_parquet),
        "artifacts": artifacts,
        "summary": {
            "required": len(REQUIRED_ARTIFACTS),
            "present": present,
            "missing": missing,
            "invalid": invalid,
            "parquet_checked": parquet_checked,
        },
    }


def _check_artifact(
    repo_root: Path,
    *,
    relative_path: str,
    kind: str,
    check_parquet: bool,
) -> dict[str, Any]:
    path = repo_root / Path(relative_path)
    result = {
        "path": Path(relative_path).as_posix(),
        "kind": kind,
        "required": True,
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "status": "valid",
        "error": None,
    }
    if not result["exists"]:
        result["status"] = "missing"
        result["error"] = "required artifact is missing"
        return result
    if result["size_bytes"] == 0:
        result["status"] = "invalid"
        result["error"] = "artifact is empty"
        return result
    if _is_git_lfs_pointer(path):
        result["status"] = "invalid"
        result["error"] = (
            "Git LFS object is not materialized; run git lfs pull"
        )
        return result
    if kind == "json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            result["status"] = "invalid"
            result["error"] = "invalid JSON: " + _portable_error(
                exc,
                repo_root,
            )
    elif kind == "parquet" and check_parquet:
        try:
            import pandas as pd

            pd.read_parquet(path)
        except ImportError as exc:
            result["status"] = "invalid"
            result["error"] = (
                "parquet check requires pandas and pyarrow: "
                + _portable_error(exc, repo_root)
            )
        except Exception as exc:
            result["status"] = "invalid"
            result["error"] = "unreadable parquet: " + _portable_error(
                exc,
                repo_root,
            )
    return result


def _is_git_lfs_pointer(path: Path) -> bool:
    try:
        prefix = path.read_bytes()[:128]
    except OSError:
        return False
    return prefix.startswith(
        b"version https://git-lfs.github.com/spec/v1"
    )


def _portable_error(exc: Exception, repo_root: Path) -> str:
    message = f"{type(exc).__name__}: {exc}"
    for root_text in {
        str(repo_root),
        repo_root.as_posix(),
    }:
        message = message.replace(root_text, ".")
    return message.replace("\\", "/")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full machine-readable JSON report.",
    )
    parser.add_argument(
        "--check-parquet",
        action="store_true",
        help="Read parquet files using pandas/pyarrow.",
    )
    return parser.parse_args(argv)


def render_text(result: dict[str, Any]) -> str:
    lines = [
        "Strict feeder RL deployment artifacts: "
        + ("PASS" if result["passed"] else "FAIL")
    ]
    for artifact in result["artifacts"]:
        lines.append(
            f"[{artifact['status'].upper()}] {artifact['path']}"
            + (
                f" ({artifact['size_bytes']} bytes)"
                if artifact["size_bytes"] is not None
                else ""
            )
        )
        if artifact["error"]:
            lines.append(f"  {artifact['error']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = check_artifacts(
        args.repo_root,
        check_parquet=args.check_parquet,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render_text(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
