from __future__ import annotations

from datetime import datetime, timedelta

from ev_core.env.entities import SimulationRequest, Station
from ev_core.recommender.eligibility import StationEligibilityFilter


def station(**overrides) -> Station:
    values = {
        "station_id": "station-1",
        "station_name": "Station 1",
        "zone_id": "zone-a",
        "transformer_id": "tx-1",
        "latitude": 56.46,
        "longitude": -2.97,
        "cp_count_total": 2,
        "connector_mix_total": "rapid;ac",
        "station_capacity_kw_assumed": 64.0,
    }
    values.update(overrides)
    return Station(**values)


def request(**metadata: object) -> SimulationRequest:
    now = datetime(2024, 6, 10, 12, 0)
    return SimulationRequest(
        request_id="request-1",
        client_request_id="client-1",
        source_type="external_live",
        arrival_ts=now,
        latest_finish_ts=now + timedelta(hours=2),
        requested_energy_kwh=12.0,
        requested_duration_minutes=30,
        preference_mode="closest",
        charger_type_preference="Rapid",
        zone_id="zone-a",
        metadata=dict(metadata),
    )


def test_public_unrestricted_station_is_eligible() -> None:
    result = StationEligibilityFilter().is_eligible(station(), request())

    assert result.eligible is True
    assert result.reason is None


def test_excluded_station_is_blocked_even_with_metadata_overrides() -> None:
    result = StationEligibilityFilter().is_eligible(
        station(exclude_from_recommendations=True),
        request(
            allow_non_public_stations=True,
            allow_fleet_only=True,
            allow_membership_sites=True,
            allow_followup_sites=True,
        ),
    )

    assert result.eligible is False
    assert result.reason == "excluded_from_recommendations"


def test_non_public_station_is_blocked_by_default() -> None:
    result = StationEligibilityFilter().is_eligible(station(is_public=False), request())

    assert result.eligible is False
    assert result.reason == "non_public"


def test_fleet_only_station_is_blocked_by_default() -> None:
    result = StationEligibilityFilter().is_eligible(station(is_fleet_only=True), request())

    assert result.eligible is False
    assert result.reason == "fleet_only"


def test_membership_station_is_blocked_by_default() -> None:
    result = StationEligibilityFilter().is_eligible(station(requires_membership=True), request())

    assert result.eligible is False
    assert result.reason == "requires_membership"


def test_followup_station_is_eligible_by_default() -> None:
    result = StationEligibilityFilter().is_eligible(station(needs_followup=True), request())

    assert result.eligible is True
    assert result.reason is None


def test_metadata_can_allow_fleet_and_membership_sites() -> None:
    filter_ = StationEligibilityFilter()

    assert filter_.is_eligible(station(is_fleet_only=True), request(allow_fleet_only=True)).eligible is True
    assert filter_.is_eligible(station(requires_membership=True), request(allow_membership_sites=True)).eligible is True


def test_metadata_can_allow_non_public_sites() -> None:
    result = StationEligibilityFilter().is_eligible(
        station(is_public=False),
        request(allow_non_public_stations=True),
    )

    assert result.eligible is True
