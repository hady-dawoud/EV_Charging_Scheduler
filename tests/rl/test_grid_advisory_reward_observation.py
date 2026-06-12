from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from ev_core.grid_advisory.contracts import GridAdvisoryResponse


def _request() -> SimpleNamespace:
    now = datetime(2024, 1, 1, 12, 0)
    return SimpleNamespace(
        request_id="request-1",
        request_timestamp=now,
        latest_finish_ts=now + timedelta(hours=2),
        requested_energy_kwh=24.0,
        charger_type="Any",
        current_soc=20.0,
        target_soc=80.0,
        battery_kwh=60.0,
        vehicle_max_ac_kw=11.0,
        vehicle_max_dc_kw=120.0,
    )


def _candidate(station_id: str = "station-a") -> SimpleNamespace:
    return SimpleNamespace(
        station_id=station_id,
        distance_km=1.0,
        estimated_wait_minutes=5,
        estimated_duration_minutes=45,
        estimated_cost_gbp=8.0,
        transformer_headroom_kw=120.0,
        current_queue=0,
        utilization=0.2,
        charger_compatible=True,
    )


def _advisory(verdict: str, risk_class: str) -> GridAdvisoryResponse:
    return GridAdvisoryResponse(
        verdict=verdict,
        risk_class=risk_class,
        v_min_pu=0.97,
        max_line_loading_percent=80.0,
        max_trafo_loading_percent=75.0,
        stress_score=0.2,
        max_allowed_kw=22.0,
        reason_codes=["test"],
        model_version="test",
        advisory_available=True,
    )


def test_observation_appends_grid_features_per_station() -> None:
    from ev_core.rl.observations import ObservationBuilder

    builder = ObservationBuilder(station_ids=["station-a", "station-b"])
    observation = builder.build(
        request=_request(),
        current_time=datetime(2024, 1, 1, 12, 0),
        station_features={"station-a": _candidate()},
        action_mask=[True, False],
        station_grid_features={"station-a": _advisory("OK", "SAFE")},
    )

    assert observation.shape == (builder.spec.vector_size,)
    assert builder.station_feature_count == 19
    assert builder.spec.vector_size == 12 + (2 * 19)


def test_grid_reject_and_violation_reduce_reward_below_grid_ok() -> None:
    from ev_core.rl.rewards import StationSelectionReward

    reward = StationSelectionReward()
    ok = reward.compute(selected_option=_candidate(), grid_advisory=_advisory("OK", "SAFE"))
    reject = reward.compute(selected_option=_candidate(), grid_advisory=_advisory("REJECT", "VIOLATION"))

    assert ok.total > reject.total
    assert ok.grid_ok_bonus > 0.0
    assert reject.grid_reject_penalty < 0.0
    assert reject.grid_violation_penalty < 0.0
