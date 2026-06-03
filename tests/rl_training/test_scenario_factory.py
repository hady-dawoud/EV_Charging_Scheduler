from __future__ import annotations

from pathlib import Path

from ev_core.config.training import RLTrainingConfig


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scenario_factory_uses_training_config_defaults() -> None:
    from ev_core.rl_training.scenario_factory import OfflineDundeeScenarioFactory

    config = RLTrainingConfig(
        split="validation",
        seed=2000,
        duration_hours=3,
        demand_level="busy",
        routing_provider_name="simple_distance",
        dynamic_pricing_enabled=True,
    )
    factory = OfflineDundeeScenarioFactory(repo_root=REPO_ROOT, training_config=config)

    request = factory.default_request()

    assert request.split == "validation"
    assert request.seed == 2000
    assert request.duration_hours == 3
    assert request.demand_level == "busy"


def test_scenario_factory_builds_reproducible_scenario_bundle() -> None:
    from ev_core.rl_training.scenario_factory import OfflineDundeeScenarioFactory, OfflineTrainingScenarioRequest

    factory = OfflineDundeeScenarioFactory(repo_root=REPO_ROOT)
    request = OfflineTrainingScenarioRequest(split="train", seed=1003, duration_hours=1, demand_level="normal")

    first = factory.build(request)
    second = factory.build(request)

    assert first.scenario == second.scenario
    assert first.metadata["split"] == "train"
    assert first.metadata["routing_provider_name"] == "simple_distance"
    assert len(first.requests) == first.scenario.request_count
