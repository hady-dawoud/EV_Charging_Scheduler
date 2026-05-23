from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

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
        seed="rl-observation-test",
    )


def test_observation_vector_size_is_deterministic_for_station_count() -> None:
    from ev_core.rl.observations import ObservationBuilder
    from ev_core.rl.scenarios import RLScenarioSampler, generate_requests_for_scenario

    bundle = _bundle()
    sampler = RLScenarioSampler(bundle=bundle)
    scenario = sampler.sample(seed=1004, duration_hours=1, demand_level="normal")
    request = generate_requests_for_scenario(scenario, request_generator=_build_request_generator())[0]

    builder = ObservationBuilder(station_ids=sorted(bundle.stations["station_id"].astype(str).tolist()))
    observation = builder.build(
        request=request,
        current_time=scenario.start_ts,
        station_features={},
        action_mask=[False] * len(builder.station_ids),
    )

    assert observation.shape == (builder.spec.vector_size,)
    assert builder.spec.vector_size == builder.spec.feature_count + (builder.spec.station_count * builder.station_feature_count)


def test_same_seed_gives_same_initial_observation() -> None:
    from ev_core.rl.observations import ObservationBuilder
    from ev_core.rl.scenarios import RLScenarioSampler, generate_requests_for_scenario

    bundle = _bundle()
    sampler = RLScenarioSampler(bundle=bundle)
    scenario = sampler.sample(seed=1012, duration_hours=1, demand_level="normal")
    request = generate_requests_for_scenario(scenario, request_generator=_build_request_generator())[0]
    station_ids = sorted(bundle.stations["station_id"].astype(str).tolist())
    builder = ObservationBuilder(station_ids=station_ids)

    first = builder.build(
        request=request,
        current_time=scenario.start_ts,
        station_features={},
        action_mask=[False] * len(station_ids),
    )
    second = builder.build(
        request=request,
        current_time=scenario.start_ts,
        station_features={},
        action_mask=[False] * len(station_ids),
    )

    assert np.array_equal(first, second)


def test_observation_contains_no_nan_or_inf_values() -> None:
    from ev_core.rl.observations import ObservationBuilder
    from ev_core.rl.scenarios import RLScenarioSampler, generate_requests_for_scenario

    bundle = _bundle()
    sampler = RLScenarioSampler(bundle=bundle)
    scenario = sampler.sample(seed=1013, duration_hours=1, demand_level="normal")
    request = generate_requests_for_scenario(scenario, request_generator=_build_request_generator())[0]
    station_ids = sorted(bundle.stations["station_id"].astype(str).tolist())
    builder = ObservationBuilder(station_ids=station_ids)

    observation = builder.build(
        request=request,
        current_time=scenario.start_ts,
        station_features={},
        action_mask=[False] * len(station_ids),
    )

    assert np.isfinite(observation).all()
