from __future__ import annotations

from ev_core.contracts.responses import RecommendationOption


def _option(station_id: str) -> RecommendationOption:
    return RecommendationOption(
        station_id=station_id,
        station_name=station_id,
        zone_id="zone-1",
        transformer_id="tx-1",
        score=1.0,
        distance_km=1.0,
        estimated_wait_minutes=0,
        estimated_duration_minutes=30,
        estimated_cost_gbp=10.0,
        transformer_headroom_kw=100.0,
        current_queue=0,
        utilization=0.25,
        charger_compatible=True,
    )


def test_random_valid_policy_selects_only_from_supplied_valid_candidates() -> None:
    from ev_core.rl.baselines import RandomValidPolicy

    options = [_option("station-a"), _option("station-b"), _option("station-c")]
    policy = RandomValidPolicy(seed=7)

    selected = policy.select_option(request_id="request-1", options=options)

    assert selected is not None
    assert selected.station_id in {option.station_id for option in options}


def test_random_valid_policy_is_deterministic_for_same_seed_and_request() -> None:
    from ev_core.rl.baselines import RandomValidPolicy

    options = [_option("station-a"), _option("station-b"), _option("station-c")]

    first = RandomValidPolicy(seed=11).select_option(request_id="request-2", options=options)
    second = RandomValidPolicy(seed=11).select_option(request_id="request-2", options=options)

    assert first == second
