from __future__ import annotations

from datetime import datetime, timedelta
import inspect
from types import SimpleNamespace

import numpy as np

from ev_core.grid_advisory.contracts import GridAdvisoryResponse
from ev_core.rl_feeder.contracts import FeederAction, FeederRequest


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


def _feeder_action(station_id: str = "station-a", secondary_area_id: str = "area-a") -> FeederAction:
    return FeederAction(
        station_id=station_id,
        secondary_area_id=secondary_area_id,
        demand_point_id=f"{station_id}-dp",
        node_id=f"{station_id}-node",
        p_base_kw=8.0,
        public_ev_capacity_kw=22.0,
        charger_kw=22.0,
        connector_type="ac",
    )


def _feeder_request() -> FeederRequest:
    now = datetime(2024, 1, 1, 12, 0)
    return FeederRequest(
        request_id="request-1",
        secondary_area_id="area-a",
        arrival_timestamp=now,
        latest_finish_timestamp=now + timedelta(hours=2),
        requested_energy_kwh=24.0,
        battery_kwh=60.0,
        current_soc=0.2,
        target_soc=0.8,
        charger_type_preference="ac",
        max_ac_kw=11.0,
        max_dc_kw=120.0,
    )


def test_station_level_rl_keeps_non_grid_aware_observation_contract() -> None:
    from ev_core.rl.observations import ObservationBuilder

    builder = ObservationBuilder(station_ids=["station-a", "station-b"])
    observation = builder.build(
        request=_request(),
        current_time=datetime(2024, 1, 1, 12, 0),
        station_features={"station-a": _candidate()},
        action_mask=[True, False],
    )

    assert observation.shape == (builder.spec.vector_size,)
    assert builder.station_feature_count == 9
    assert builder.spec.vector_size == 12 + (2 * 9)
    assert "station_grid_features" not in inspect.signature(builder.build).parameters


def test_station_level_rl_reward_keeps_non_grid_aware_contract() -> None:
    from ev_core.rl.rewards import StationSelectionReward

    reward = StationSelectionReward()
    served = reward.compute(selected_option=_candidate())
    invalid = reward.compute(invalid_action=True)

    assert served.total > invalid.total
    assert "grid_advisory" not in inspect.signature(reward.compute).parameters


def test_feeder_observation_owns_grid_advisory_features() -> None:
    from ev_core.rl_feeder.observations import FeederObservationBuilder

    actions = [_feeder_action("station-a", "area-a"), _feeder_action("station-b", "area-b")]
    builder = FeederObservationBuilder(actions=actions)
    request = _feeder_request()
    without_grid = builder.build(request=request, action_mask=[True, False])
    with_grid = builder.build(
        request=request,
        action_mask=[True, False],
        grid_advisories={"station-a": _advisory("OK", "SAFE")},
    )

    assert with_grid.shape == (builder.spec.vector_size,)
    assert builder.action_feature_count == 30
    assert builder.spec.vector_size == 10 + (2 * 30)
    assert not np.array_equal(without_grid, with_grid)


def test_feeder_reward_owns_grid_reject_and_violation_terms() -> None:
    from ev_core.rl_feeder.rewards import FeederStationSelectionReward

    reward = FeederStationSelectionReward()
    action = _feeder_action()
    request = _feeder_request()
    ok = reward.compute(selected_action=action, request=request, grid_advisory=_advisory("OK", "SAFE"))
    reject = reward.compute(
        selected_action=action,
        request=request,
        grid_advisory=GridAdvisoryResponse(
            verdict="REJECT",
            risk_class="VIOLATION",
            stress_score=0.9,
            delta_v_min_pu=-0.08,
            voltage_violation_count=1,
            line_overload_count=1,
            trafo_overload_count=1,
            curtailment_required_kw=12.0,
            opf_feasible=False,
            opf_curtailment_kwh=6.0,
            advisory_available=True,
            physical_truth_level="area_pf",
            label_source_kind="area_reuse",
        ),
    )

    assert ok.total > reject.total
    assert reject.violation_penalty < 0.0
    assert reject.opf_penalty < 0.0
    assert reject.curtailment_penalty < 0.0
