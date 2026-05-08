from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta

for module_name in ("numpy", "pandas"):
    module = types.ModuleType(module_name)
    module.DataFrame = object
    sys.modules.setdefault(module_name, module)

from ev_core.env.entities import SimulationRequest, Station, StationRuntimeState
from ev_core.recommender.candidates import CandidateBuilder
from ev_core.recommender.ranker import CandidateContext


def station(
    station_id: str,
    *,
    connector_mix_total: str = "rapid;ac",
    cp_count_total: int = 2,
    station_capacity_kw_assumed: float = 64.0,
    transformer_id: str = "tx-1",
    is_public: bool = True,
    is_fleet_only: bool = False,
    requires_membership: bool = False,
    needs_followup: bool = False,
    exclude_from_recommendations: bool = False,
) -> Station:
    return Station(
        station_id=station_id,
        station_name=station_id.replace("-", " ").title(),
        zone_id="zone-a",
        transformer_id=transformer_id,
        latitude=56.46,
        longitude=-2.97,
        cp_count_total=cp_count_total,
        connector_mix_total=connector_mix_total,
        station_capacity_kw_assumed=station_capacity_kw_assumed,
        is_public=is_public,
        is_fleet_only=is_fleet_only,
        requires_membership=requires_membership,
        needs_followup=needs_followup,
        exclude_from_recommendations=exclude_from_recommendations,
    )


def request(*, latest_finish_delta_minutes: int = 180, requested_energy_kwh: float = 8.0) -> SimulationRequest:
    now = datetime(2024, 6, 10, 12, 0)
    return SimulationRequest(
        request_id="request-1",
        client_request_id="client-1",
        source_type="external_live",
        arrival_ts=now,
        latest_finish_ts=now + timedelta(minutes=latest_finish_delta_minutes),
        requested_energy_kwh=requested_energy_kwh,
        requested_duration_minutes=30,
        preference_mode="closest",
        charger_type_preference="Rapid",
        zone_id="zone-a",
    )


def request_with_metadata(**metadata: object) -> SimulationRequest:
    sim_request = request()
    sim_request.metadata.update(metadata)
    return sim_request


def request_with_vehicle_limits(
    *,
    latest_finish_delta_minutes: int = 180,
    requested_energy_kwh: float = 40.0,
    vehicle_max_ac_kw: float | None = None,
    vehicle_max_dc_kw: float | None = None,
) -> SimulationRequest:
    sim_request = request(
        latest_finish_delta_minutes=latest_finish_delta_minutes,
        requested_energy_kwh=requested_energy_kwh,
    )
    sim_request.vehicle_max_ac_kw = vehicle_max_ac_kw
    sim_request.vehicle_max_dc_kw = vehicle_max_dc_kw
    return sim_request


def build(
    *,
    stations: tuple[Station, ...],
    runtime_states: dict[str, StationRuntimeState] | None = None,
    wait_by_station: dict[str, int] | None = None,
    distance_by_station: dict[str, float] | None = None,
    headroom_by_transformer: dict[str, float] | None = None,
    compatibility_by_station: dict[str, bool] | None = None,
    sim_request: SimulationRequest | None = None,
    only_station_id: str | None = None,
    station_effective_power_kw=None,
    compatible_available_port_count=None,
) -> list[CandidateContext]:
    runtime_states = runtime_states or {item.station_id: StationRuntimeState(station=item) for item in stations}
    wait_by_station = wait_by_station or {}
    distance_by_station = distance_by_station or {}
    headroom_by_transformer = headroom_by_transformer or {}
    compatibility_by_station = compatibility_by_station or {}
    return CandidateBuilder().build(
        request=sim_request or request(),
        stations=stations,
        stations_runtime=runtime_states,
        current_time=datetime(2024, 6, 10, 12, 0),
        only_station_id=only_station_id,
        distance_to_station_km=lambda req, st: distance_by_station.get(st.station_id, 1.25),
        estimate_station_wait_minutes=lambda station_id: wait_by_station.get(station_id, 0),
        current_price_per_kwh=lambda: 0.31,
        current_transformer_headroom=lambda transformer_id: headroom_by_transformer.get(transformer_id, 125.0),
        is_charger_compatible=lambda requested_type, connector_mix: compatibility_by_station.get(
            str(connector_mix).split(";")[0],
            "rapid" in str(connector_mix).lower(),
        ),
        station_effective_power_kw=station_effective_power_kw,
        compatible_available_port_count=compatible_available_port_count,
    )


def test_candidate_builder_returns_candidate_context_with_existing_fields() -> None:
    target = station("rapid-station", connector_mix_total="rapid;ac", transformer_id="tx-rapid")
    runtime_state = StationRuntimeState(station=target)
    runtime_state.active_session_ids.extend(["active-1"])
    runtime_state.queue_request_ids.extend(["queued-1", "queued-2"])

    candidates = build(
        stations=(target,),
        runtime_states={target.station_id: runtime_state},
        wait_by_station={target.station_id: 30},
        distance_by_station={target.station_id: 2.75},
        headroom_by_transformer={"tx-rapid": 321.5},
    )

    assert len(candidates) == 1
    option = candidates[0]
    assert option.station_id == "rapid-station"
    assert option.station_name == "Rapid Station"
    assert option.zone_id == "zone-a"
    assert option.transformer_id == "tx-rapid"
    assert option.distance_km == 2.75
    assert option.estimated_wait_minutes == 30
    assert option.estimated_duration_minutes == 15
    assert option.estimated_cost_gbp == 2.48
    assert option.transformer_headroom_kw == 321.5
    assert option.current_queue == 2
    assert option.utilization == 0.5
    assert option.charger_compatible is True
    assert option.metadata == {"connector_mix_total": "rapid;ac"}


def test_candidate_builder_filters_incompatible_stations() -> None:
    compatible = station("compatible", connector_mix_total="rapid")
    incompatible = station("incompatible", connector_mix_total="ac")

    candidates = build(stations=(compatible, incompatible))

    assert [candidate.station_id for candidate in candidates] == ["compatible"]


def test_candidate_builder_filters_candidates_outside_deadline_window() -> None:
    too_slow = station("too-slow", cp_count_total=0, station_capacity_kw_assumed=0.0)
    feasible = station("feasible", cp_count_total=2, station_capacity_kw_assumed=64.0)

    candidates = build(
        stations=(too_slow, feasible),
        sim_request=request(latest_finish_delta_minutes=60),
        wait_by_station={"too-slow": 0, "feasible": 30},
    )

    assert [candidate.station_id for candidate in candidates] == ["feasible"]


def test_candidate_builder_respects_only_station_id() -> None:
    first = station("first")
    second = station("second")

    assert [candidate.station_id for candidate in build(stations=(first, second), only_station_id="second")] == ["second"]
    assert build(stations=(first, second), only_station_id="missing") == []


def test_candidate_builder_preserves_duration_rounding_and_minimum() -> None:
    fallback_power = station("fallback-power", cp_count_total=0, station_capacity_kw_assumed=0.0)
    very_fast = station("very-fast", cp_count_total=1, station_capacity_kw_assumed=350.0)

    fallback_candidate = build(stations=(fallback_power,))[0]
    minimum_candidate = build(stations=(very_fast,), sim_request=request(requested_energy_kwh=1.0))[0]

    assert fallback_candidate.estimated_duration_minutes == 75
    assert minimum_candidate.estimated_duration_minutes == 15


def test_candidate_builder_uses_vehicle_dc_limit_for_rapid_station_duration() -> None:
    rapid = station("rapid", connector_mix_total="rapid", cp_count_total=2, station_capacity_kw_assumed=300.0)

    without_vehicle_limit = build(stations=(rapid,), sim_request=request(requested_energy_kwh=40.0))[0]
    with_vehicle_limit = build(
        stations=(rapid,),
        sim_request=request_with_vehicle_limits(requested_energy_kwh=40.0, vehicle_max_dc_kw=50.0),
    )[0]

    assert without_vehicle_limit.estimated_duration_minutes == 15
    assert with_vehicle_limit.estimated_duration_minutes == 45


def test_candidate_builder_filters_candidate_when_vehicle_limit_misses_deadline() -> None:
    rapid = station("rapid", connector_mix_total="rapid", cp_count_total=2, station_capacity_kw_assumed=300.0)

    candidates = build(
        stations=(rapid,),
        sim_request=request_with_vehicle_limits(
            latest_finish_delta_minutes=30,
            requested_energy_kwh=40.0,
            vehicle_max_dc_kw=50.0,
        ),
    )

    assert candidates == []


def test_candidate_builder_skips_ineligible_station_before_candidate_output() -> None:
    public = station("public")
    fleet = station("fleet", is_fleet_only=True)

    candidates = build(stations=(public, fleet))

    assert [candidate.station_id for candidate in candidates] == ["public"]


def test_candidate_builder_allows_fleet_station_when_request_metadata_allows_it() -> None:
    fleet = station("fleet", is_fleet_only=True)

    candidates = build(stations=(fleet,), sim_request=request_with_metadata(allow_fleet_only=True))

    assert [candidate.station_id for candidate in candidates] == ["fleet"]


def test_candidate_builder_blocks_restricted_station_for_normal_external_live_request() -> None:
    restricted = station("restricted", is_public=False, requires_membership=True)

    candidates = build(stations=(restricted,))

    assert candidates == []


def test_candidate_builder_skips_station_when_no_compatible_port_is_currently_available() -> None:
    ac_only = station("ac-only", connector_mix_total="ac", station_capacity_kw_assumed=22.0, cp_count_total=1)

    candidates = build(
        stations=(ac_only,),
        sim_request=request_with_vehicle_limits(requested_energy_kwh=20.0, vehicle_max_ac_kw=11.0),
        compatible_available_port_count=lambda req, st: 0,
        station_effective_power_kw=lambda req, st: 11.0,
    )

    assert candidates == []


def test_candidate_builder_uses_cp_aware_effective_power_when_provided() -> None:
    mixed = station("mixed", connector_mix_total="ac;rapid", station_capacity_kw_assumed=172.0, cp_count_total=2)

    candidate = build(
        stations=(mixed,),
        sim_request=request_with_vehicle_limits(requested_energy_kwh=20.0, vehicle_max_ac_kw=11.0),
        compatible_available_port_count=lambda req, st: 1,
        station_effective_power_kw=lambda req, st: 22.0,
    )[0]

    assert candidate.estimated_duration_minutes == 60
