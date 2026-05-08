from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.vehicles.profiles import get_default_vehicle_profiles


REQUEST_PARAMS = {
    "arrival_distributions": {
        "hour_share": {"12": 1.0},
        "month_share": {"6": 1.0},
        "weekday_type_share": {"weekday": 1.0, "weekend": 0.0},
    },
    "zone_level_demand_share": {
        "request_share": {
            "zone-a": 0.7,
            "zone-b": 0.3,
        }
    },
    "user_preference_mode": {
        "realized_share": {
            "closest": 0.4,
            "cheapest": 0.3,
            "fastest": 0.3,
        }
    },
    "requested_energy_kwh_summary": {
        "p10": 6.0,
        "p25": 10.0,
        "median": 18.0,
        "p75": 28.0,
        "p90": 40.0,
        "p95": 48.0,
    },
    "requested_duration_minutes_summary": {
        "p10": 15.0,
        "p25": 30.0,
        "median": 45.0,
        "p75": 60.0,
        "p90": 90.0,
        "p95": 120.0,
    },
    "slack_minutes_summary": {
        "p10": 0.0,
        "p25": 15.0,
        "median": 30.0,
        "p75": 45.0,
        "p90": 60.0,
        "p95": 120.0,
    },
}


def stations() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            station_id="station-a",
            station_name="Station A",
            zone_id="zone-a",
            latitude=56.46,
            longitude=-2.97,
            cp_count_total=2,
            connector_mix_total="ac;rapid",
            sessions_total=100,
        ),
        SimpleNamespace(
            station_id="station-b",
            station_name="Station B",
            zone_id="zone-b",
            latitude=56.48,
            longitude=-2.93,
            cp_count_total=1,
            connector_mix_total="ac",
            sessions_total=50,
        ),
    ]


def generator(seed: int | str = 123) -> SyntheticLiveRequestGenerator:
    return SyntheticLiveRequestGenerator(
        request_generator_params=REQUEST_PARAMS,
        stations=stations(),
        vehicle_profiles=get_default_vehicle_profiles(),
        seed=seed,
    )


def test_generate_one_returns_valid_external_live_request_with_metadata() -> None:
    request = generator().generate_one(datetime(2024, 6, 10, 12, 0), index=1)

    assert isinstance(request, ExternalChargingRequest)
    assert request.source_type == "external_live"
    assert request.metadata["generator_type"] == "synthetic_live"
    assert request.metadata["generator_version"] == "synthetic_live_v1"
    assert request.metadata["anchor_station_id"] in {"station-a", "station-b"}
    assert request.metadata["anchor_zone_id"] == request.zone_id
    assert request.request_id == "synthetic-live-20240610T120000-000001"
    assert request.client_request_id == request.request_id


def test_generate_one_is_deterministic_for_same_seed_timestamp_and_index() -> None:
    first = generator(seed="stable").generate_one(datetime(2024, 6, 10, 12, 0), index=4)
    second = generator(seed="stable").generate_one(datetime(2024, 6, 10, 12, 0), index=4)
    third = generator(seed="stable").generate_one(datetime(2024, 6, 10, 12, 0), index=5)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.request_id != third.request_id
    assert first.client_request_id != third.client_request_id


def test_generated_soc_energy_and_vehicle_fields_match_selected_profile() -> None:
    request = generator().generate_one(datetime(2024, 6, 10, 12, 0), index=2)
    profile = get_default_vehicle_profiles()[request.vehicle_profile_id]
    expected_energy = round(((request.target_soc - request.current_soc) / 100.0) * profile.battery_kwh, 3)

    assert request.target_soc > request.current_soc
    assert request.battery_kwh == profile.battery_kwh
    assert request.vehicle_max_ac_kw == profile.ac_max_kw
    assert request.vehicle_max_dc_kw == profile.dc_max_kw
    assert abs(request.requested_energy_kwh - expected_energy) <= 0.001


def test_generated_location_preference_and_charger_type_are_contract_valid() -> None:
    request = generator().generate_one(datetime(2024, 6, 10, 12, 0), index=3)

    assert 56.43 <= request.current_latitude <= 56.51
    assert -3.02 <= request.current_longitude <= -2.88
    assert request.zone_id in {"zone-a", "zone-b"}
    assert request.preference_mode in {"closest", "cheapest", "fastest"}
    assert request.charger_type in {"Any", "AC", "Rapid"}


def test_generate_batch_returns_requested_count_with_valid_distinct_ids() -> None:
    requests = generator().generate_batch(
        start_ts=datetime(2024, 6, 10, 12, 0),
        end_ts=datetime(2024, 6, 10, 14, 0),
        count=5,
    )

    assert len(requests) == 5
    assert len({request.request_id for request in requests}) == 5
    assert all(isinstance(request, ExternalChargingRequest) for request in requests)
    assert all(datetime(2024, 6, 10, 12, 0) <= request.request_timestamp <= datetime(2024, 6, 10, 14, 0) for request in requests)
