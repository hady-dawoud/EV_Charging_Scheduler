from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from ev_core.vehicles.profiles import get_default_vehicle_profiles


def _build_fake_bundle() -> SimpleNamespace:
    return SimpleNamespace(
        stations=pd.DataFrame(
            [
                {"station_id": "a", "zone_id": "zone-1"},
                {"station_id": "b", "zone_id": "zone-1"},
            ]
        ),
        chargepoints=pd.DataFrame(
            [
                {"cp_id": "cp-1", "station_id": "a", "assumed_port_kw": 22.0},
                {"cp_id": "cp-2", "station_id": "a", "assumed_port_kw": 50.0},
                {"cp_id": "cp-3", "station_id": "b", "assumed_port_kw": 7.0},
            ]
        ),
        zones=pd.DataFrame([{"zone_id": "zone-1"}]),
        transformers=pd.DataFrame([{"transformer_id": "tx-1"}]),
        request_generator_params={
            "request_counts_by_year": {"2024": 8760},
            "requested_energy_kwh_summary": {"mean": 18.0},
            "requested_duration_minutes_summary": {"mean": 60.0},
        },
    )


def test_build_utilization_bands_returns_expected_active_car_ranges() -> None:
    from ev_core.analysis.rl_demand_realism import build_utilization_bands

    bands = build_utilization_bands(chargepoint_count=10)

    assert bands["normal"]["min_active_cars"] == 3.0
    assert bands["normal"]["max_active_cars"] == 6.0
    assert bands["busy"]["min_active_cars"] == 6.0
    assert bands["busy"]["max_active_cars"] == 8.0
    assert bands["stress"]["min_active_cars"] == 8.0
    assert bands["stress"]["max_active_cars"] == 10.0


def test_suggested_request_ranges_increase_with_busier_utilization_bands() -> None:
    from ev_core.analysis.rl_demand_realism import suggest_episode_request_ranges

    ranges = suggest_episode_request_ranges(
        chargepoint_count=12,
        avg_duration_minutes=90.0,
        horizons_hours=(3,),
    )

    normal = ranges[3]["normal"]
    busy = ranges[3]["busy"]
    stress = ranges[3]["stress"]

    assert normal["min_requests"] < busy["min_requests"] < stress["min_requests"]
    assert normal["max_requests"] < busy["max_requests"] < stress["max_requests"]


def test_build_demand_realism_summary_uses_bundle_counts_without_hardcoded_cp_assumption() -> None:
    from ev_core.analysis.rl_demand_realism import build_demand_realism_summary

    summary = build_demand_realism_summary(
        bundle=_build_fake_bundle(),
        vehicle_profiles=get_default_vehicle_profiles(),
    )

    assert summary["station_count"] == 2
    assert summary["chargepoint_count"] == 3
    assert summary["connector_count"] == 3
    assert summary["total_port_capacity_kw"] == 79.0
    assert summary["vehicle_profile_count"] == 4
    assert summary["estimated_active_cars"] == 1.0


def test_build_demand_realism_summary_does_not_crash_on_small_fake_data() -> None:
    from ev_core.analysis.rl_demand_realism import build_demand_realism_summary

    summary = build_demand_realism_summary(
        bundle=_build_fake_bundle(),
        vehicle_profiles=get_default_vehicle_profiles(),
    )

    assert "historical_request_rate_summary" in summary
    assert "scenario_request_ranges" in summary
