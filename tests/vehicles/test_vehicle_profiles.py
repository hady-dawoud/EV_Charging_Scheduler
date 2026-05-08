from __future__ import annotations

import pytest

from ev_core.vehicles.profiles import DEFAULT_VEHICLE_PROFILES, get_default_vehicle_profiles, get_vehicle_profile


def test_default_vehicle_profile_catalog_contains_expected_profiles() -> None:
    profiles = get_default_vehicle_profiles()

    assert set(profiles) == {"small_ev", "mid_ev", "large_ev", "van_ev"}


def test_default_vehicle_profiles_have_positive_capabilities() -> None:
    for profile in DEFAULT_VEHICLE_PROFILES.values():
        assert profile.battery_kwh > 0
        assert profile.ac_max_kw > 0
        assert profile.dc_max_kw > 0
        assert profile.market_share > 0


def test_get_vehicle_profile_returns_known_profile() -> None:
    profile = get_vehicle_profile("mid_ev")

    assert profile.vehicle_profile_id == "mid_ev"
    assert profile.vehicle_name


def test_get_vehicle_profile_rejects_unknown_profile() -> None:
    with pytest.raises(KeyError):
        get_vehicle_profile("missing")
