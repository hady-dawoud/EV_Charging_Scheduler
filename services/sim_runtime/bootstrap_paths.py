from __future__ import annotations

import sys
from pathlib import Path


def bootstrap_repo_paths() -> Path:
    current = Path(__file__).resolve()

    for candidate in [current.parent, *current.parents]:
        ev_core_pkg = candidate / "packages" / "ev_core" / "src" / "ev_core"
        sim_runtime_pkg = candidate / "services" / "sim_runtime"

        if ev_core_pkg.exists() and sim_runtime_pkg.exists():
            repo_root = candidate
            ev_core_src = repo_root / "packages" / "ev_core" / "src"

            for path in (repo_root, ev_core_src):
                path_str = str(path)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)

            return repo_root

    raise RuntimeError(
        "Could not locate repository root containing packages/ev_core/src and services/sim_runtime."
    )