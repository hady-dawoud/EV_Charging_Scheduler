from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.vehicles.profiles import get_default_vehicle_profiles


REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _bundle():
    return DundeeSimulationRepository(REPO_ROOT).load_bundle()


def _build_request_generator() -> SyntheticLiveRequestGenerator:
    bundle = _bundle()
    return SyntheticLiveRequestGenerator(
        request_generator_params=bundle.request_generator_params,
        stations=bundle.stations.to_dict(orient="records"),
        vehicle_profiles=get_default_vehicle_profiles(),
        seed="rl-sampler-test",
    )


def test_sampler_respects_fixed_train_validation_and_test_seed_ranges() -> None:
    from ev_core.rl.scenarios import RLScenarioSampler

    sampler = RLScenarioSampler(bundle=_bundle())

    train = sampler.sample(seed=1000)
    validation = sampler.sample(seed=2000)
    test = sampler.sample(seed=3000)

    assert train.split == "train"
    assert validation.split == "validation"
    assert test.split == "test"


def test_same_seed_produces_same_scenario() -> None:
    from ev_core.rl.scenarios import RLScenarioSampler

    sampler = RLScenarioSampler(bundle=_bundle())

    first = sampler.sample(seed=1010)
    second = sampler.sample(seed=1010)

    assert first == second


def test_different_seed_changes_scenario() -> None:
    from ev_core.rl.scenarios import RLScenarioSampler

    sampler = RLScenarioSampler(bundle=_bundle())

    first = sampler.sample(seed=1010)
    second = sampler.sample(seed=1011)

    assert first != second


def test_request_count_ranges_increase_from_normal_to_busy_to_stress() -> None:
    from ev_core.rl.scenarios import RLScenarioSampler

    sampler = RLScenarioSampler(bundle=_bundle())

    normal = sampler.get_request_count_range(duration_hours=3, demand_level="normal")
    busy = sampler.get_request_count_range(duration_hours=3, demand_level="busy")
    stress = sampler.get_request_count_range(duration_hours=3, demand_level="stress")

    assert normal["min_requests"] <= normal["max_requests"] <= busy["max_requests"]
    assert busy["min_requests"] <= busy["max_requests"] <= stress["max_requests"]
    assert normal["min_requests"] < busy["min_requests"] < stress["min_requests"]


def test_generate_requests_for_scenario_returns_valid_requests_with_scenario_metadata() -> None:
    from ev_core.rl.scenarios import RLScenarioSampler, generate_requests_for_scenario

    sampler = RLScenarioSampler(bundle=_bundle())
    scenario = sampler.sample(seed=1005, duration_hours=1, demand_level="normal")

    requests = generate_requests_for_scenario(
        scenario,
        request_generator=_build_request_generator(),
    )

    assert len(requests) == scenario.request_count
    assert requests[0].metadata["scenario_id"] == scenario.scenario_id
    assert requests[0].metadata["scenario_seed"] == scenario.seed
    assert requests[0].metadata["split"] == scenario.split
    assert requests[0].metadata["demand_level"] == scenario.demand_level
    assert requests[0].metadata["demand_multiplier"] == scenario.demand_multiplier
    assert all(scenario.start_ts <= request.request_timestamp <= scenario.end_ts for request in requests)
