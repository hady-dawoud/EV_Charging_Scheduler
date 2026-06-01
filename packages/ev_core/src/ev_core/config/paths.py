from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPathsConfig:
    repo_root: Path
    data_dir: Path
    raw_data_dir: Path
    interim_data_dir: Path
    processed_data_dir: Path
    outputs_dir: Path
    runtime_outputs_dir: Path
    rl_outputs_dir: Path
    model_dir: Path
    rl_model_dir: Path


def _infer_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / 'packages' / 'ev_core' / 'src').exists() and (parent / 'data').exists():
            return parent
    return current.parents[5]


def default_project_paths(repo_root: Path | str | None = None) -> ProjectPathsConfig:
    root = Path(repo_root).resolve() if repo_root is not None else _infer_repo_root()
    data_dir = root / 'data'
    outputs_dir = root / 'outputs'
    model_dir = root / 'models'
    return ProjectPathsConfig(
        repo_root=root,
        data_dir=data_dir,
        raw_data_dir=data_dir / 'raw',
        interim_data_dir=data_dir / 'interim',
        processed_data_dir=data_dir / 'processed',
        outputs_dir=outputs_dir,
        runtime_outputs_dir=outputs_dir / 'runtime',
        rl_outputs_dir=outputs_dir / 'rl',
        model_dir=model_dir,
        rl_model_dir=model_dir / 'rl',
    )
