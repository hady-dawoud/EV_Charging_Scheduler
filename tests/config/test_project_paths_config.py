from pathlib import Path

from ev_core.config.paths import default_project_paths


def test_default_project_paths_use_expected_layout() -> None:
    cfg = default_project_paths()
    assert cfg.data_dir.name == 'data'
    assert cfg.raw_data_dir.name == 'raw'
    assert cfg.interim_data_dir.name == 'interim'
    assert cfg.processed_data_dir.name == 'processed'
    assert cfg.outputs_dir.name == 'outputs'
    assert cfg.runtime_outputs_dir.name == 'runtime'
    assert cfg.rl_outputs_dir == cfg.outputs_dir / 'rl'
    assert cfg.rl_model_dir == cfg.model_dir / 'rl'


def test_default_project_paths_accept_explicit_root(tmp_path: Path) -> None:
    cfg = default_project_paths(repo_root=tmp_path)
    assert cfg.repo_root == tmp_path.resolve()
    assert cfg.rl_outputs_dir == tmp_path.resolve() / 'outputs' / 'rl'
