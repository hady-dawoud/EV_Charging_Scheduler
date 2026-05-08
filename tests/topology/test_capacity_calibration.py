from __future__ import annotations

import pandas as pd
import pytest

from ev_core.topology.capacity_calibration import (
    STANDARD_CAPACITY_KW,
    build_capacity_recommendations,
    capacity_warning_flags,
    recommend_transformer_capacity_kw,
)


def test_realistic_capacity_is_at_least_max_single_cp_and_standard_size() -> None:
    capacity = recommend_transformer_capacity_kw(
        connected_cp_kw=180.0,
        max_single_cp_kw=150.0,
        attached_station_count=1,
        attached_cp_count=2,
        scenario_type="realistic",
    )

    assert capacity >= 150.0
    assert capacity in STANDARD_CAPACITY_KW


def test_multi_station_realistic_capacity_is_not_below_300kw() -> None:
    capacity = recommend_transformer_capacity_kw(
        connected_cp_kw=88.0,
        max_single_cp_kw=22.0,
        attached_station_count=3,
        attached_cp_count=4,
        scenario_type="realistic",
    )

    assert capacity >= 300.0


def test_realistic_capacity_is_not_below_stress_capacity() -> None:
    realistic = recommend_transformer_capacity_kw(
        connected_cp_kw=650.0,
        max_single_cp_kw=150.0,
        attached_station_count=5,
        attached_cp_count=13,
        scenario_type="realistic",
    )
    stress = recommend_transformer_capacity_kw(
        connected_cp_kw=650.0,
        max_single_cp_kw=150.0,
        attached_station_count=5,
        attached_cp_count=13,
        scenario_type="stress",
    )

    assert realistic >= stress


def test_capacity_rounds_up_to_next_standard_size() -> None:
    capacity = recommend_transformer_capacity_kw(
        connected_cp_kw=900.0,
        max_single_cp_kw=150.0,
        attached_station_count=4,
        attached_cp_count=10,
        scenario_type="realistic",
    )

    assert capacity == 1250.0


def test_warning_flags_detect_low_capacity_cases() -> None:
    flags = capacity_warning_flags(
        current_capacity_kw=120.0,
        connected_cp_kw=400.0,
        max_single_cp_kw=150.0,
        attached_station_count=2,
    )

    assert "capacity_below_max_single_cp" in flags
    assert "capacity_below_half_connected_cp_kw" in flags
    assert "capacity_below_300kw_multi_station" in flags


def test_build_capacity_recommendations_sums_cp_load_and_counts() -> None:
    station_rows = pd.DataFrame(
        [
            {"station_id": "station_a", "transformer_id": "tx_a", "station_capacity_kw_assumed": 30.0},
            {"station_id": "station_b", "transformer_id": "tx_a", "station_capacity_kw_assumed": 50.0},
        ]
    )
    chargepoint_rows = pd.DataFrame(
        [
            {"station_id": "station_a", "assumed_port_kw": 22.0},
            {"station_id": "station_b", "assumed_port_kw": 50.0},
            {"station_id": "station_b", "assumed_port_kw": 150.0},
        ]
    )
    transformer_rows = pd.DataFrame(
        [
            {
                "transformer_id": "tx_a",
                "transformer_name": "Transformer A",
                "zone_id": "zone_a",
                "transformer_capacity_kw_assumed": 150.0,
            }
        ]
    )

    recommendation = build_capacity_recommendations(
        station_rows=station_rows,
        chargepoint_rows=chargepoint_rows,
        transformer_rows=transformer_rows,
    )[0]

    assert recommendation.connected_cp_kw == 222.0
    assert recommendation.max_single_cp_kw == 150.0
    assert recommendation.attached_cp_count == 3
    assert recommendation.attached_station_count == 2


def test_build_capacity_recommendations_falls_back_to_station_capacity_proxy() -> None:
    station_rows = pd.DataFrame(
        [
            {"station_id": "station_a", "transformer_id": "tx_a", "station_capacity_kw_assumed": 30.0},
            {"station_id": "station_b", "transformer_id": "tx_a", "station_capacity_kw_assumed": 50.0},
        ]
    )
    transformer_rows = pd.DataFrame(
        [
            {
                "transformer_id": "tx_a",
                "transformer_name": "Transformer A",
                "zone_id": "zone_a",
                "transformer_capacity_kw_assumed": 150.0,
            }
        ]
    )

    recommendation = build_capacity_recommendations(
        station_rows=station_rows,
        chargepoint_rows=pd.DataFrame(),
        transformer_rows=transformer_rows,
    )[0]

    assert recommendation.connected_cp_kw == 80.0
    assert recommendation.attached_cp_count == 0


def test_build_capacity_recommendations_requires_core_columns() -> None:
    with pytest.raises(ValueError, match="station rows are missing required columns"):
        build_capacity_recommendations(
            station_rows=pd.DataFrame([{"station_id": "station_a"}]),
            chargepoint_rows=pd.DataFrame(),
            transformer_rows=pd.DataFrame(
                [
                    {
                        "transformer_id": "tx_a",
                        "transformer_name": "Transformer A",
                        "zone_id": "zone_a",
                        "transformer_capacity_kw_assumed": 150.0,
                    }
                ]
            ),
        )
