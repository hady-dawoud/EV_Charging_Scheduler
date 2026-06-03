from pathlib import Path

import pytest

from ev_core.config.deployment import RLDeploymentConfig, rl_deployment_config_from_env
from ev_core.config.training import RLTrainingConfig, rl_training_config_from_env


def test_rl_training_paths_can_be_set_explicitly() -> None:
    cfg = RLTrainingConfig(
        checkpoint_dir=Path('outputs/rl/checkpoints'),
        evaluation_dir=Path('outputs/rl/evaluations'),
        tensorboard_dir=Path('outputs/rl/tensorboard'),
        figures_dir=Path('outputs/rl/figures'),
    )
    assert cfg.checkpoint_dir == Path('outputs/rl/checkpoints')
    assert cfg.evaluation_dir == Path('outputs/rl/evaluations')


def test_rl_deployment_checkpoint_can_be_set_explicitly() -> None:
    cfg = RLDeploymentConfig(checkpoint_path=Path('models/rl/policy.zip'))
    assert cfg.checkpoint_path == Path('models/rl/policy.zip')


def test_env_parsing_for_training_and_deployment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('RL_CHECKPOINT_DIR', 'outputs/rl/checkpoints')
    monkeypatch.setenv('RL_EVALUATION_DIR', 'outputs/rl/evaluations')
    monkeypatch.setenv('RL_TENSORBOARD_DIR', 'outputs/rl/tensorboard')
    monkeypatch.setenv('RL_FIGURES_DIR', 'outputs/rl/figures')
    monkeypatch.setenv('RL_POLICY_CHECKPOINT_PATH', 'models/rl/policy.zip')
    monkeypatch.setenv('RL_POLICY_FAIL_CLOSED', 'true')

    train_cfg = rl_training_config_from_env()
    deploy_cfg = rl_deployment_config_from_env()

    assert train_cfg.checkpoint_dir == Path('outputs/rl/checkpoints')
    assert train_cfg.figures_dir == Path('outputs/rl/figures')
    assert deploy_cfg.checkpoint_path == Path('models/rl/policy.zip')
    assert deploy_cfg.fail_closed is True
