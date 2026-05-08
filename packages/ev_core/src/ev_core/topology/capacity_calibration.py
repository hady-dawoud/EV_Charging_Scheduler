"""Synthetic transformer capacity calibration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Any


STANDARD_CAPACITY_KW = (150, 300, 315, 500, 800, 1000, 1250, 1600, 2000, 2500)


@dataclass(frozen=True)
class TransformerCapacityInput:
    transformer_id: str
    transformer_name: str
    zone_id: str
    attached_station_ids: tuple[str, ...]
    current_capacity_kw: float
    connected_cp_kw: float
    max_single_cp_kw: float
    attached_cp_count: int
    attached_station_count: int


@dataclass(frozen=True)
class TransformerCapacityRecommendation:
    transformer_id: str
    current_capacity_kw: float
    connected_cp_kw: float
    max_single_cp_kw: float
    recommended_realistic_capacity_kw: float
    recommended_stress_capacity_kw: float
    connected_load_ratio_current: float
    warning_flags: tuple[str, ...]
    transformer_name: str = ""
    zone_id: str = ""
    attached_station_ids: tuple[str, ...] = ()
    attached_cp_count: int = 0
    attached_station_count: int = 0


def recommend_transformer_capacity_kw(
    *,
    connected_cp_kw: float,
    max_single_cp_kw: float,
    attached_station_count: int,
    attached_cp_count: int,
    scenario_type: str,
) -> float:
    """Recommend a synthetic active-power transformer capacity in standard steps."""

    connected = max(float(connected_cp_kw), 0.0)
    max_single = max(float(max_single_cp_kw), 0.0)
    station_count = max(int(attached_station_count), 0)
    cp_count = max(int(attached_cp_count), 0)
    scenario = str(scenario_type).strip().lower()

    if scenario == "realistic":
        diversity_factor = _diversity_factor(max_single_cp_kw=max_single, connected_cp_kw=connected, attached_cp_count=cp_count)
        required_kw = max(
            max_single * 1.25,
            connected * diversity_factor / 0.80,
            300.0 if station_count > 1 else 150.0,
        )
    elif scenario == "stress":
        required_kw = max(
            max_single,
            connected * 0.45,
            150.0,
        )
    else:
        raise ValueError(f"unsupported capacity scenario_type: {scenario_type}")
    return float(_round_up_standard_capacity(required_kw))


def capacity_warning_flags(
    *,
    current_capacity_kw: float,
    connected_cp_kw: float,
    max_single_cp_kw: float,
    attached_station_count: int,
) -> tuple[str, ...]:
    """Return warning flags for synthetic capacities that look too constrained."""

    current = float(current_capacity_kw)
    connected = max(float(connected_cp_kw), 0.0)
    max_single = max(float(max_single_cp_kw), 0.0)
    station_count = max(int(attached_station_count), 0)
    flags: list[str] = []
    if current < max_single:
        flags.append("capacity_below_max_single_cp")
    if connected > 0 and current < connected * 0.5:
        flags.append("capacity_below_half_connected_cp_kw")
    if station_count > 1 and current < 300.0:
        flags.append("capacity_below_300kw_multi_station")
    if max_single >= 50.0 and connected > 0 and current < connected * 0.70:
        flags.append("capacity_below_connected_rapid_load")
    return tuple(flags)


def build_capacity_recommendations(
    *,
    station_rows,
    chargepoint_rows,
    transformer_rows,
) -> list[TransformerCapacityRecommendation]:
    """Build capacity recommendations from repository station, CP, and transformer rows."""

    _require_columns(station_rows, ("station_id", "transformer_id"), "station rows")
    _require_columns(
        transformer_rows,
        ("transformer_id", "transformer_name", "zone_id", "transformer_capacity_kw_assumed"),
        "transformer rows",
    )
    chargepoints_available = chargepoint_rows is not None and not getattr(chargepoint_rows, "empty", True)
    if chargepoints_available:
        _require_columns(chargepoint_rows, ("station_id", "assumed_port_kw"), "chargepoint rows")

    stations = station_rows.copy()
    stations["station_id"] = stations["station_id"].astype(str)
    stations["transformer_id"] = stations["transformer_id"].astype(str)

    chargepoints = None
    if chargepoints_available:
        chargepoints = chargepoint_rows.copy()
        chargepoints["station_id"] = chargepoints["station_id"].astype(str)
        chargepoints["assumed_port_kw"] = _numeric_series(chargepoints["assumed_port_kw"])

    recommendations: list[TransformerCapacityRecommendation] = []
    for row in transformer_rows.to_dict(orient="records"):
        transformer_id = str(row["transformer_id"])
        attached = stations[stations["transformer_id"] == transformer_id].copy()
        attached_station_ids = tuple(attached["station_id"].astype(str))

        if chargepoints is not None:
            cp_rows = chargepoints[chargepoints["station_id"].isin(attached_station_ids)]
            connected_cp_kw = float(cp_rows["assumed_port_kw"].sum()) if not cp_rows.empty else 0.0
            max_single_cp_kw = float(cp_rows["assumed_port_kw"].max()) if not cp_rows.empty else 0.0
            attached_cp_count = int(len(cp_rows))
        else:
            connected_cp_kw, max_single_cp_kw, attached_cp_count = _station_capacity_proxy(attached)

        if connected_cp_kw <= 0:
            connected_cp_kw, max_single_cp_kw, attached_cp_count = _station_capacity_proxy(attached)

        current_capacity_kw = float(row["transformer_capacity_kw_assumed"])
        attached_station_count = int(len(attached_station_ids))
        ratio = connected_cp_kw / current_capacity_kw if current_capacity_kw > 0 else inf
        realistic = recommend_transformer_capacity_kw(
            connected_cp_kw=connected_cp_kw,
            max_single_cp_kw=max_single_cp_kw,
            attached_station_count=attached_station_count,
            attached_cp_count=attached_cp_count,
            scenario_type="realistic",
        )
        stress = recommend_transformer_capacity_kw(
            connected_cp_kw=connected_cp_kw,
            max_single_cp_kw=max_single_cp_kw,
            attached_station_count=attached_station_count,
            attached_cp_count=attached_cp_count,
            scenario_type="stress",
        )
        recommendations.append(
            TransformerCapacityRecommendation(
                transformer_id=transformer_id,
                transformer_name=str(row["transformer_name"]),
                zone_id=str(row["zone_id"]),
                attached_station_ids=attached_station_ids,
                current_capacity_kw=current_capacity_kw,
                connected_cp_kw=round(connected_cp_kw, 3),
                max_single_cp_kw=round(max_single_cp_kw, 3),
                attached_cp_count=attached_cp_count,
                attached_station_count=attached_station_count,
                recommended_realistic_capacity_kw=realistic,
                recommended_stress_capacity_kw=stress,
                connected_load_ratio_current=round(ratio, 6),
                warning_flags=capacity_warning_flags(
                    current_capacity_kw=current_capacity_kw,
                    connected_cp_kw=connected_cp_kw,
                    max_single_cp_kw=max_single_cp_kw,
                    attached_station_count=attached_station_count,
                ),
            )
        )
    return recommendations


def _diversity_factor(*, max_single_cp_kw: float, connected_cp_kw: float, attached_cp_count: int) -> float:
    if max_single_cp_kw >= 150.0:
        return 0.95
    if max_single_cp_kw >= 100.0:
        return 0.85
    if max_single_cp_kw >= 50.0 or connected_cp_kw >= 150.0 or attached_cp_count >= 6:
        return 0.70
    return 0.55


def _round_up_standard_capacity(required_kw: float) -> int:
    for capacity in STANDARD_CAPACITY_KW:
        if required_kw <= capacity:
            return capacity
    return STANDARD_CAPACITY_KW[-1]


def _station_capacity_proxy(stations) -> tuple[float, float, int]:
    if "station_capacity_kw_assumed" not in stations.columns or stations.empty:
        return 0.0, 0.0, 0
    values = _numeric_series(stations["station_capacity_kw_assumed"]).fillna(0.0)
    return float(values.sum()), float(values.max()), 0


def _require_columns(frame: Any, columns: tuple[str, ...], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing required columns: {', '.join(missing)}")


def _numeric_series(series):
    import pandas as pd

    return pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)


__all__ = [
    "STANDARD_CAPACITY_KW",
    "TransformerCapacityInput",
    "TransformerCapacityRecommendation",
    "build_capacity_recommendations",
    "capacity_warning_flags",
    "recommend_transformer_capacity_kw",
]
