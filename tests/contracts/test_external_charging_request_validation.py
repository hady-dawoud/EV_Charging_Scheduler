from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ev_core.contracts.requests import ExternalChargingRequest


def valid_payload(**overrides):
    payload = {
        "client_request_id": "mobile-1",
        "request_timestamp": datetime(2024, 6, 10, 12, 0),
        "current_latitude": 56.462,
        "current_longitude": -2.9707,
        "target_soc": 80.0,
        "current_soc": 45.0,
        "battery_kwh": 82.0,
        "requested_energy_kwh": 28.7,
        "preference_mode": "closest",
        "charger_type": "Rapid",
        "latest_finish_ts": datetime(2024, 6, 10, 14, 0),
        "source_type": "external_live",
        "request_id": "mobile-live-1",
        "zone_id": "zone_central_waterfront",
        "metadata": {"channel": "mobile-app"},
    }
    payload.update(overrides)
    return payload


def assert_invalid(**overrides) -> None:
    with pytest.raises(ValidationError):
        ExternalChargingRequest.model_validate(valid_payload(**overrides))


def test_mobile_style_payload_validates() -> None:
    request = ExternalChargingRequest.model_validate(valid_payload())

    assert request.requested_energy_kwh == 28.7
    assert request.charger_type == "Rapid"
    assert request.vehicle_profile_id is None
    assert request.vehicle_max_ac_kw is None
    assert request.vehicle_max_dc_kw is None


def test_timezone_aware_timestamps_are_normalized_to_naive_utc() -> None:
    request = ExternalChargingRequest.model_validate(
        valid_payload(
            request_timestamp=datetime(2024, 6, 10, 13, 0, tzinfo=timezone.utc),
            latest_finish_ts=datetime(2024, 6, 10, 15, 0, tzinfo=timezone.utc),
        )
    )

    assert request.request_timestamp == datetime(2024, 6, 10, 13, 0)
    assert request.latest_finish_ts == datetime(2024, 6, 10, 15, 0)
    assert request.request_timestamp.tzinfo is None


def test_missing_requested_energy_is_inferred_from_soc_and_battery() -> None:
    request = ExternalChargingRequest.model_validate(
        valid_payload(
            current_soc=20.0,
            target_soc=65.0,
            battery_kwh=60.0,
            requested_energy_kwh=None,
        )
    )

    assert request.requested_energy_kwh == 27.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"current_soc": -1.0},
        {"target_soc": 101.0},
        {"current_soc": 80.0, "target_soc": 80.0, "requested_energy_kwh": 0.0},
        {"current_soc": 90.0, "target_soc": 80.0, "requested_energy_kwh": 0.0},
    ],
)
def test_soc_domain_validation(overrides) -> None:
    assert_invalid(**overrides)


@pytest.mark.parametrize("battery_kwh", [0.0, -1.0, 251.0])
def test_battery_capacity_validation(battery_kwh: float) -> None:
    assert_invalid(battery_kwh=battery_kwh)


def test_large_but_plausible_battery_capacity_passes() -> None:
    request = ExternalChargingRequest.model_validate(
        valid_payload(
            current_soc=20.0,
            target_soc=80.0,
            battery_kwh=250.0,
            requested_energy_kwh=150.0,
        )
    )

    assert request.battery_kwh == 250.0


@pytest.mark.parametrize("requested_energy_kwh", [36.0, 36.3, 37.7])
def test_requested_energy_matching_soc_derived_value_passes(requested_energy_kwh: float) -> None:
    request = ExternalChargingRequest.model_validate(
        valid_payload(
            current_soc=20.0,
            target_soc=80.0,
            battery_kwh=60.0,
            requested_energy_kwh=requested_energy_kwh,
        )
    )

    assert request.requested_energy_kwh == requested_energy_kwh


@pytest.mark.parametrize("requested_energy_kwh", [0.0, -1.0])
def test_requested_energy_must_be_positive(requested_energy_kwh: float) -> None:
    assert_invalid(requested_energy_kwh=requested_energy_kwh)


def test_requested_energy_greater_than_battery_fails() -> None:
    assert_invalid(
        current_soc=20.0,
        target_soc=80.0,
        battery_kwh=60.0,
        requested_energy_kwh=61.0,
    )


def test_large_requested_energy_mismatch_fails() -> None:
    assert_invalid(
        current_soc=20.0,
        target_soc=80.0,
        battery_kwh=60.0,
        requested_energy_kwh=5.0,
    )


@pytest.mark.parametrize(
    "latest_finish_ts",
    [
        datetime(2024, 6, 10, 11, 59),
        datetime(2024, 6, 10, 12, 0),
    ],
)
def test_latest_finish_must_be_after_request_timestamp(latest_finish_ts: datetime) -> None:
    assert_invalid(latest_finish_ts=latest_finish_ts)


@pytest.mark.parametrize(
    "overrides",
    [
        {"current_latitude": -91.0},
        {"current_latitude": 91.0},
        {"current_longitude": -181.0},
        {"current_longitude": 181.0},
    ],
)
def test_coordinate_bounds_validation(overrides) -> None:
    assert_invalid(**overrides)


@pytest.mark.parametrize("charger_type", ["Any", "any", "AC", "ac", "DC", "dc", "Rapid", "UltraRapid", "ultra_rapid"])
def test_supported_charger_types_pass(charger_type: str) -> None:
    request = ExternalChargingRequest.model_validate(valid_payload(charger_type=charger_type))

    assert request.charger_type == charger_type


def test_unsupported_charger_type_fails() -> None:
    assert_invalid(charger_type="diesel")


def test_optional_vehicle_profile_fields_validate_when_present() -> None:
    request = ExternalChargingRequest.model_validate(
        valid_payload(
            vehicle_profile_id="large_ev",
            vehicle_max_ac_kw=11.0,
            vehicle_max_dc_kw=150.0,
        )
    )

    assert request.vehicle_profile_id == "large_ev"
    assert request.vehicle_max_ac_kw == 11.0
    assert request.vehicle_max_dc_kw == 150.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"vehicle_max_ac_kw": 0.0},
        {"vehicle_max_ac_kw": -1.0},
        {"vehicle_max_ac_kw": 51.0},
        {"vehicle_max_dc_kw": 0.0},
        {"vehicle_max_dc_kw": -1.0},
        {"vehicle_max_dc_kw": 501.0},
    ],
)
def test_vehicle_max_power_bounds(overrides) -> None:
    assert_invalid(**overrides)
