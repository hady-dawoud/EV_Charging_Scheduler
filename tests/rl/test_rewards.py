from __future__ import annotations

from ev_core.contracts.responses import RecommendationOption


def _option(
    *,
    cost: float = 10.0,
    distance: float = 2.0,
    wait: int = 10,
    duration: int = 40,
    headroom: float = 120.0,
) -> RecommendationOption:
    return RecommendationOption(
        station_id="station-a",
        station_name="Station A",
        zone_id="zone-1",
        transformer_id="tx-1",
        score=1.0,
        distance_km=distance,
        estimated_wait_minutes=wait,
        estimated_duration_minutes=duration,
        estimated_cost_gbp=cost,
        transformer_headroom_kw=headroom,
        current_queue=0,
        utilization=0.2,
        charger_compatible=True,
    )


def test_valid_served_reward_is_greater_than_invalid_action_reward() -> None:
    from ev_core.rl.rewards import StationSelectionReward

    reward = StationSelectionReward()
    served = reward.compute(selected_option=_option())
    invalid = reward.compute(invalid_action=True)

    assert served.total > invalid.total


def test_higher_cost_distance_and_wait_reduce_reward() -> None:
    from ev_core.rl.rewards import StationSelectionReward

    reward = StationSelectionReward()
    better = reward.compute(selected_option=_option(cost=8.0, distance=1.0, wait=5, duration=30))
    worse = reward.compute(selected_option=_option(cost=20.0, distance=6.0, wait=30, duration=90))

    assert better.total > worse.total


def test_low_headroom_reduces_reward() -> None:
    from ev_core.rl.rewards import StationSelectionReward

    reward = StationSelectionReward()
    high_headroom = reward.compute(selected_option=_option(headroom=150.0))
    low_headroom = reward.compute(selected_option=_option(headroom=5.0))

    assert high_headroom.total > low_headroom.total
