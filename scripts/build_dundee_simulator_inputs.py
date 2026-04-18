"""Build Dundee simulator replay requests and exogenous 15-minute inputs.

This script is intentionally Dundee-only and additive. It does not modify any
canonical cleaned datasets or application code. The outputs are simulation-ready
artifacts for the EV-side environment:

- request replay tables for 2023 and 2024
- request-generation priors and replay notes
- 15-minute exogenous background-load, price, and optional PV tables
- QC summaries for dropped sessions and replay coverage
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

LOGGER = logging.getLogger("dundee_simulator_inputs")

TIMEBASE_MINUTES = 15
REQUEST_YEARS = [2023, 2024]
YEAR_START = pd.Timestamp("2023-01-01 00:00:00")
YEAR_END = pd.Timestamp("2024-12-31 23:45:00")

USER_PREFERENCE_DISTRIBUTIONS: dict[str, dict[str, float]] = {
    "ac": {"closest": 0.50, "cheapest": 0.35, "fastest": 0.15},
    "rapid": {"closest": 0.25, "cheapest": 0.15, "fastest": 0.60},
    "ultra_rapid": {"closest": 0.15, "cheapest": 0.10, "fastest": 0.75},
    "default": {"closest": 0.40, "cheapest": 0.30, "fastest": 0.30},
}

PREFERENCE_SLACK_FACTORS = {
    "fastest": 0.00,
    "closest": 0.35,
    "cheapest": 0.70,
}

CHARGER_TYPE_PREFERENCE_MAP = {
    "ac": "AC",
    "rapid": "Rapid",
    "ultra_rapid": "UltraRapid",
}

ZONE_BACKGROUND_MULTIPLIERS = {
    "zone_central_waterfront": 1.08,
    "zone_west_lochee": 0.98,
    "zone_north_inner": 0.95,
    "zone_east_corridor": 1.00,
}

MONTHLY_BACKGROUND_MULTIPLIERS = {
    1: 1.08,
    2: 1.06,
    3: 1.03,
    4: 1.00,
    5: 0.98,
    6: 0.97,
    7: 0.98,
    8: 0.99,
    9: 1.00,
    10: 1.02,
    11: 1.05,
    12: 1.08,
}

PV_DAYLIGHT_HOURS = {
    1: 8.0,
    2: 9.5,
    3: 11.5,
    4: 13.5,
    5: 15.5,
    6: 16.5,
    7: 16.0,
    8: 14.5,
    9: 12.5,
    10: 10.5,
    11: 9.0,
    12: 8.0,
}

PV_SEASONAL_PEAK = {
    1: 0.38,
    2: 0.46,
    3: 0.58,
    4: 0.72,
    5: 0.84,
    6: 0.92,
    7: 0.90,
    8: 0.80,
    9: 0.66,
    10: 0.54,
    11: 0.42,
    12: 0.34,
}


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line interface."""

    parser = argparse.ArgumentParser(description="Build Dundee replay requests and exogenous simulator inputs.")
    parser.add_argument("--clean-csv", type=Path, default=Path("data/interim/dundee_sessions_clean.csv"))
    parser.add_argument("--model-ready-csv", type=Path, default=Path("data/interim/dundee_sessions_model_ready.csv"))
    parser.add_argument("--station-master", type=Path, default=Path("data/processed/station_master.csv"))
    parser.add_argument(
        "--station-locations-verified",
        type=Path,
        default=Path("data/processed/station_locations_verified.csv"),
    )
    parser.add_argument("--zones-csv", type=Path, default=Path("data/processed/zones.csv"))
    parser.add_argument("--station-zone-map-csv", type=Path, default=Path("data/processed/station_zone_map.csv"))
    parser.add_argument("--transformers-csv", type=Path, default=Path("data/processed/transformers.csv"))
    parser.add_argument(
        "--transformer-station-map-csv",
        type=Path,
        default=Path("data/processed/transformer_station_map.csv"),
    )
    parser.add_argument(
        "--station-capacity-assumptions-csv",
        type=Path,
        default=Path("data/processed/station_capacity_assumptions.csv"),
    )
    parser.add_argument("--request-replay-2023-csv", type=Path, default=Path("data/processed/request_replay_2023.csv"))
    parser.add_argument("--request-replay-2024-csv", type=Path, default=Path("data/processed/request_replay_2024.csv"))
    parser.add_argument(
        "--request-generator-params-json",
        type=Path,
        default=Path("data/processed/request_generator_params.json"),
    )
    parser.add_argument(
        "--background-load-15min-csv",
        type=Path,
        default=Path("data/processed/background_load_15min.csv"),
    )
    parser.add_argument(
        "--price-table-15min-csv",
        type=Path,
        default=Path("data/processed/price_table_15min.csv"),
    )
    parser.add_argument("--pv-profile-15min-csv", type=Path, default=Path("data/processed/pv_profile_15min.csv"))
    parser.add_argument(
        "--request-replay-notes-md",
        type=Path,
        default=Path("outputs/qc/dundee_request_replay_notes.md"),
    )
    parser.add_argument(
        "--request-replay-summary-csv",
        type=Path,
        default=Path("outputs/qc/dundee_request_replay_summary.csv"),
    )
    parser.add_argument(
        "--request-replay-summary-md",
        type=Path,
        default=Path("outputs/qc/dundee_request_replay_summary.md"),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def configure_logging(level: str) -> None:
    """Configure script logging."""

    logging.basicConfig(level=getattr(logging, level.upper()), format="%(levelname)s %(name)s: %(message)s")


def ensure_output_dirs(paths: list[Path]) -> None:
    """Create output parent directories if they do not exist."""

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def round_up_to_timebase(minutes: float, timebase_minutes: int = TIMEBASE_MINUTES) -> int:
    """Round a duration up to the 15-minute simulator time base."""

    clipped = max(float(minutes), float(timebase_minutes))
    return int(math.ceil(clipped / timebase_minutes) * timebase_minutes)


def stable_fraction(value: str) -> float:
    """Map a string to a stable fractional bucket in [0, 1)."""

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12)


def native(value: Any) -> Any:
    """Convert pandas and NumPy values to plain Python types for JSON output."""

    if isinstance(value, dict):
        return {str(key): native(inner_value) for key, inner_value in value.items()}
    if isinstance(value, list):
        return [native(item) for item in value]
    if isinstance(value, tuple):
        return [native(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def load_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load Dundee clean/model/session-mapping inputs required for replay generation."""

    required_paths = [
        args.clean_csv,
        args.model_ready_csv,
        args.station_master,
        args.station_locations_verified,
        args.zones_csv,
        args.station_zone_map_csv,
        args.transformers_csv,
        args.transformer_station_map_csv,
    ]
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing required Dundee input: {path}")

    clean = pd.read_csv(
        args.clean_csv,
        usecols=["session_id", "station_id", "arrival_ts", "energy_kwh", "session_minutes"],
        parse_dates=["arrival_ts"],
    )
    clean = clean[clean["arrival_ts"].dt.year.isin(REQUEST_YEARS)].copy()

    model_ready = pd.read_csv(
        args.model_ready_csv,
        usecols=[
            "session_id",
            "source_year",
            "station_name",
            "station_id",
            "cp_id",
            "connector_type",
            "energy_kwh",
            "arrival_ts",
            "approx_departure_ts",
            "session_minutes",
            "assumed_connector_limit_kw",
        ],
        parse_dates=["arrival_ts", "approx_departure_ts"],
    )
    model_ready = model_ready[model_ready["arrival_ts"].dt.year.isin(REQUEST_YEARS)].copy()

    station_master = pd.read_csv(
        args.station_master,
        usecols=["station_id", "station_name", "cp_count_total", "connector_mix_total", "station_max_power_kw_proxy"],
    )
    verified_locations = pd.read_csv(
        args.station_locations_verified,
        usecols=["station_id", "verification_status", "location_confidence_final"],
    )
    zones = pd.read_csv(args.zones_csv)
    station_zone_map = pd.read_csv(
        args.station_zone_map_csv,
        usecols=["station_id", "zone_id", "zone_name", "zone_description"],
    )
    transformers = pd.read_csv(args.transformers_csv)
    transformer_station_map = pd.read_csv(
        args.transformer_station_map_csv,
        usecols=["station_id", "transformer_id", "transformer_name", "transformer_map_label"],
    )

    spatial_map = (
        station_master.merge(station_zone_map, on="station_id", how="left")
        .merge(transformer_station_map, on="station_id", how="left")
        .merge(verified_locations, on="station_id", how="left")
    )
    return clean, model_ready, spatial_map, transformers, zones


def assign_user_preference_mode(session_id: str, connector_type: str) -> str:
    """Assign a deterministic user preference mode from a documented connector-based distribution."""

    distribution = USER_PREFERENCE_DISTRIBUTIONS.get(str(connector_type), USER_PREFERENCE_DISTRIBUTIONS["default"])
    bucket = stable_fraction(f"{session_id}|{connector_type}")
    cumulative = 0.0
    for mode, share in distribution.items():
        cumulative += share
        if bucket <= cumulative:
            return mode
    return list(distribution.keys())[-1]


def build_replay_candidates(model_ready: pd.DataFrame, spatial_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build replay requests from Dundee model-ready sessions and capture model-stage drops."""

    replay = model_ready.merge(spatial_map, on=["station_id", "station_name"], how="left")
    replay["request_year"] = replay["arrival_ts"].dt.year.astype("int64")
    replay["arrival_slot"] = replay["arrival_ts"].dt.floor(f"{TIMEBASE_MINUTES}min")
    replay["latest_finish_ts"] = replay["approx_departure_ts"]
    replay["latest_finish_slot"] = replay["latest_finish_ts"].dt.ceil(f"{TIMEBASE_MINUTES}min")
    replay["aligned_window_minutes"] = (
        (replay["latest_finish_slot"] - replay["arrival_slot"]).dt.total_seconds() / 60
    ).round().astype("int64")

    replay["requested_energy_kwh"] = pd.to_numeric(replay["energy_kwh"], errors="coerce")
    replay["assumed_connector_limit_kw"] = pd.to_numeric(replay["assumed_connector_limit_kw"], errors="coerce")
    replay["technical_min_duration_minutes"] = replay.apply(
        lambda row: round_up_to_timebase((row["requested_energy_kwh"] / row["assumed_connector_limit_kw"]) * 60),
        axis=1,
    )
    replay["user_preference_mode"] = replay.apply(
        lambda row: assign_user_preference_mode(str(row["session_id"]), str(row["connector_type"])),
        axis=1,
    )
    replay["charger_type_preference"] = replay["connector_type"].map(CHARGER_TYPE_PREFERENCE_MAP).fillna("Any")

    missing_spatial_mapping = replay["zone_id"].isna() | replay["transformer_id"].isna()
    nonpositive_aligned_window = replay["aligned_window_minutes"] <= 0
    technical_duration_exceeds_window = replay["technical_min_duration_minutes"] > replay["aligned_window_minutes"]

    replay["drop_reason"] = pd.Series(pd.NA, index=replay.index, dtype="object")
    replay.loc[missing_spatial_mapping, "drop_reason"] = "missing_spatial_mapping"
    replay.loc[replay["drop_reason"].isna() & nonpositive_aligned_window, "drop_reason"] = "nonpositive_aligned_window"
    replay.loc[
        replay["drop_reason"].isna() & technical_duration_exceeds_window,
        "drop_reason",
    ] = "technical_duration_exceeds_window"

    dropped_model = replay.loc[replay["drop_reason"].notna(), ["session_id", "request_year", "drop_reason"]].copy()
    replay = replay.loc[replay["drop_reason"].isna()].copy()

    replay["slack_available_minutes"] = (
        replay["aligned_window_minutes"] - replay["technical_min_duration_minutes"]
    ).clip(lower=0)
    replay["requested_duration_minutes"] = replay.apply(
        lambda row: int(
            row["technical_min_duration_minutes"]
            + math.floor(
                row["slack_available_minutes"] * PREFERENCE_SLACK_FACTORS[row["user_preference_mode"]] / TIMEBASE_MINUTES
            )
            * TIMEBASE_MINUTES
        ),
        axis=1,
    )
    replay["requested_duration_minutes"] = replay["requested_duration_minutes"].clip(lower=TIMEBASE_MINUTES)
    replay["slack_minutes"] = replay["aligned_window_minutes"] - replay["requested_duration_minutes"]
    replay["is_weekend"] = replay["arrival_ts"].dt.dayofweek >= 5
    replay["arrival_hour"] = replay["arrival_ts"].dt.hour.astype("int64")
    replay["arrival_month"] = replay["arrival_ts"].dt.month.astype("int64")
    replay["arrival_weekday_name"] = replay["arrival_ts"].dt.day_name()
    replay["weekday_type"] = np.where(replay["is_weekend"], "weekend", "weekday")

    replay = replay.sort_values(["request_year", "arrival_ts", "session_id"], kind="stable").reset_index(drop=True)
    replay["request_seq"] = replay.groupby("request_year").cumcount() + 1
    replay["request_id"] = replay.apply(
        lambda row: f"dundee_replay_{int(row['request_year'])}_{int(row['request_seq']):06d}",
        axis=1,
    )
    replay["source_session_id"] = replay["session_id"]

    columns = [
        "request_id",
        "source_session_id",
        "arrival_ts",
        "arrival_slot",
        "zone_id",
        "zone_name",
        "transformer_id",
        "transformer_name",
        "station_id",
        "requested_energy_kwh",
        "requested_duration_minutes",
        "latest_finish_ts",
        "latest_finish_slot",
        "user_preference_mode",
        "charger_type_preference",
        "request_year",
        "source_year",
        "station_name",
        "cp_id",
        "connector_type",
        "assumed_connector_limit_kw",
        "aligned_window_minutes",
        "technical_min_duration_minutes",
        "slack_minutes",
        "weekday_type",
        "arrival_weekday_name",
        "arrival_hour",
        "arrival_month",
        "cp_count_total",
        "connector_mix_total",
        "station_max_power_kw_proxy",
        "verification_status",
        "location_confidence_final",
    ]
    return replay[columns], dropped_model


def summarize_distribution(series: pd.Series) -> dict[str, float]:
    """Summarize a numeric series with simulator-friendly percentile statistics."""

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "min": 0.0,
            "p10": 0.0,
            "p25": 0.0,
            "p75": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "max": 0.0,
        }
    return {
        "count": int(numeric.count()),
        "mean": round(float(numeric.mean()), 3),
        "median": round(float(numeric.median()), 3),
        "std": round(float(numeric.std(ddof=0)), 3),
        "min": round(float(numeric.min()), 3),
        "p10": round(float(numeric.quantile(0.10)), 3),
        "p25": round(float(numeric.quantile(0.25)), 3),
        "p75": round(float(numeric.quantile(0.75)), 3),
        "p90": round(float(numeric.quantile(0.90)), 3),
        "p95": round(float(numeric.quantile(0.95)), 3),
        "max": round(float(numeric.max()), 3),
    }


def build_request_generator_params(
    replay: pd.DataFrame,
    dropped_summary: pd.DataFrame,
    output_path: Path,
) -> dict[str, Any]:
    """Create request-generation priors from the combined Dundee replay set."""

    arrival_hour_share = (
        replay["arrival_hour"].value_counts(normalize=True).sort_index().round(6).rename_axis("hour").astype(float).to_dict()
    )
    weekday_type_share = (
        replay["weekday_type"].value_counts(normalize=True).sort_index().round(6).rename_axis("weekday_type").astype(float).to_dict()
    )
    month_share = (
        replay["arrival_month"].value_counts(normalize=True).sort_index().round(6).rename_axis("month").astype(float).to_dict()
    )
    zone_request_share = (
        replay["zone_id"].value_counts(normalize=True).sort_index().round(6).rename_axis("zone_id").astype(float).to_dict()
    )
    zone_energy_share = (
        replay.groupby("zone_id")["requested_energy_kwh"].sum().div(replay["requested_energy_kwh"].sum()).round(6).astype(float).to_dict()
    )
    preference_share = (
        replay["user_preference_mode"].value_counts(normalize=True).sort_index().round(6).astype(float).to_dict()
    )
    preference_by_connector = {
        connector_type: (
            subset["user_preference_mode"].value_counts(normalize=True).sort_index().round(6).astype(float).to_dict()
        )
        for connector_type, subset in replay.groupby("connector_type", sort=True)
    }

    params = {
        "version": "dundee_v1_replay_priors",
        "timebase_minutes": TIMEBASE_MINUTES,
        "source_years": REQUEST_YEARS,
        "request_counts_by_year": replay["request_year"].value_counts().sort_index().astype(int).to_dict(),
        "arrival_distributions": {
            "hour_share": arrival_hour_share,
            "weekday_type_share": weekday_type_share,
            "month_share": month_share,
        },
        "requested_energy_kwh_summary": summarize_distribution(replay["requested_energy_kwh"]),
        "requested_duration_minutes_summary": summarize_distribution(replay["requested_duration_minutes"]),
        "aligned_window_minutes_summary": summarize_distribution(replay["aligned_window_minutes"]),
        "slack_minutes_summary": summarize_distribution(replay["slack_minutes"]),
        "zone_level_demand_share": {
            "request_share": zone_request_share,
            "energy_share": zone_energy_share,
        },
        "user_preference_mode": {
            "assignment_method": "stable SHA-256 hash bucket by session_id and connector_type",
            "connector_type_distributions": USER_PREFERENCE_DISTRIBUTIONS,
            "realized_share": preference_share,
            "realized_share_by_connector_type": preference_by_connector,
        },
        "charger_type_preference_mapping": {
            "mapping": CHARGER_TYPE_PREFERENCE_MAP,
            "fallback": "Any",
        },
        "dropped_session_counts": [
            {
                "request_year": int(row["request_year"]),
                "drop_reason": row["drop_reason"],
                "count": int(row["count"]),
            }
            for _, row in dropped_summary.iterrows()
        ],
        "assumptions": {
            "requested_duration_minutes": (
                "Derived from requested energy at the observed connector limit, rounded to 15-minute slots, "
                "then expanded within the observed dwell window based on the deterministic user preference mode."
            ),
            "latest_finish_ts": "Observed approximate departure timestamp from the Dundee model-ready session.",
            "latest_finish_slot": "Observed latest finish rounded up to the 15-minute simulator time base.",
        },
        "exogenous_inputs": {
            "background_load": (
                "Transformer-level deterministic load profile scaled by synthetic transformer capacity, "
                "time-of-day block, weekday/weekend, zone multiplier, and a mild seasonal multiplier."
            ),
            "price_table": "System-wide deterministic TOU tariff in GBP/kWh on the same 15-minute time base.",
            "pv_profile": "Optional normalized daylight-shaped PV capacity factor profile on the same 15-minute time base.",
        },
    }
    output_path.write_text(json.dumps(native(params), indent=2) + "\n", encoding="utf-8")
    return params


def build_dropped_summary(clean: pd.DataFrame, model_ready: pd.DataFrame, dropped_model: pd.DataFrame) -> pd.DataFrame:
    """Build dropped-session counts relative to the clean Dundee sessions for 2023 and 2024."""

    clean_subset = clean.copy()
    clean_subset["request_year"] = clean_subset["arrival_ts"].dt.year.astype("int64")

    model_subset = model_ready[["session_id", "arrival_ts"]].copy()
    model_subset["request_year"] = model_subset["arrival_ts"].dt.year.astype("int64")

    dropped_before_model = clean_subset.loc[~clean_subset["session_id"].isin(model_subset["session_id"]), ["session_id", "request_year"]].copy()
    dropped_before_model["drop_reason"] = "excluded_by_model_ready_qc"

    combined = pd.concat([dropped_before_model, dropped_model], ignore_index=True)
    if combined.empty:
        return pd.DataFrame(columns=["request_year", "drop_reason", "count"])
    summary = combined.groupby(["request_year", "drop_reason"], as_index=False).size()
    return summary.rename(columns={"size": "count"}).sort_values(["request_year", "drop_reason"], kind="stable").reset_index(drop=True)


def build_summary_rows(replay: pd.DataFrame, dropped_summary: pd.DataFrame) -> pd.DataFrame:
    """Build a tidy CSV summary for Dundee replay QC."""

    rows: list[dict[str, Any]] = []

    for request_year, count in replay["request_year"].value_counts().sort_index().items():
        rows.append(
            {
                "section": "request_counts_by_year",
                "dimension": str(request_year),
                "metric": "request_count",
                "value": int(count),
                "notes": "Final replay requests after simulator-input filtering.",
            }
        )

    zone_counts = replay.groupby(["zone_id", "zone_name"], as_index=False).size().rename(columns={"size": "request_count"})
    for _, row in zone_counts.sort_values("request_count", ascending=False, kind="stable").iterrows():
        rows.append(
            {
                "section": "requests_by_zone",
                "dimension": f"{row['zone_id']}|{row['zone_name']}",
                "metric": "request_count",
                "value": int(row["request_count"]),
                "notes": "Combined 2023-2024 replay request count.",
            }
        )

    station_counts = replay.groupby(["station_id", "station_name"], as_index=False).size().rename(columns={"size": "request_count"})
    for _, row in station_counts.sort_values(["request_count", "station_name"], ascending=[False, True], kind="stable").iterrows():
        rows.append(
            {
                "section": "requests_by_station",
                "dimension": f"{row['station_id']}|{row['station_name']}",
                "metric": "request_count",
                "value": int(row["request_count"]),
                "notes": "Combined 2023-2024 replay request count.",
            }
        )

    for hour, share in replay["arrival_hour"].value_counts(normalize=True).sort_index().items():
        rows.append(
            {
                "section": "arrival_histogram_summary",
                "dimension": f"hour_{int(hour):02d}",
                "metric": "share",
                "value": round(float(share), 6),
                "notes": "Combined 2023-2024 arrival-hour share.",
            }
        )

    for name, summary in [
        ("requested_energy_kwh", summarize_distribution(replay["requested_energy_kwh"])),
        ("requested_duration_minutes", summarize_distribution(replay["requested_duration_minutes"])),
        ("slack_minutes", summarize_distribution(replay["slack_minutes"])),
    ]:
        for metric, value in summary.items():
            rows.append(
                {
                    "section": f"{name}_summary",
                    "dimension": "overall",
                    "metric": metric,
                    "value": value,
                    "notes": "Combined 2023-2024 replay summary statistic.",
                }
            )

    for _, row in dropped_summary.iterrows():
        rows.append(
            {
                "section": "dropped_sessions",
                "dimension": f"{int(row['request_year'])}|{row['drop_reason']}",
                "metric": "count",
                "value": int(row["count"]),
                "notes": "Dropped relative to the clean Dundee sessions for the same year.",
            }
        )

    return pd.DataFrame(rows)


def build_background_load(transformers: pd.DataFrame) -> pd.DataFrame:
    """Build a deterministic transformer-level 15-minute background load profile."""

    time_index = pd.date_range(YEAR_START, YEAR_END, freq=f"{TIMEBASE_MINUTES}min")
    timeline = pd.DataFrame({"timestamp": time_index})
    timeline["date"] = timeline["timestamp"].dt.date.astype(str)
    timeline["year"] = timeline["timestamp"].dt.year.astype("int64")
    timeline["month"] = timeline["timestamp"].dt.month.astype("int64")
    timeline["weekday_name"] = timeline["timestamp"].dt.day_name()
    timeline["is_weekend"] = timeline["timestamp"].dt.dayofweek >= 5
    timeline["hour"] = timeline["timestamp"].dt.hour.astype("int64")
    timeline["minute"] = timeline["timestamp"].dt.minute.astype("int64")
    timeline["quarter_hour_slot"] = ((timeline["hour"] * 60) + timeline["minute"]) // TIMEBASE_MINUTES

    weekday_conditions = [
        timeline["hour"].between(0, 5),
        timeline["hour"].between(6, 8),
        timeline["hour"].between(9, 15),
        timeline["hour"].between(16, 20),
    ]
    weekend_conditions = [
        timeline["hour"].between(0, 6),
        timeline["hour"].between(7, 10),
        timeline["hour"].between(11, 17),
        timeline["hour"].between(18, 21),
    ]
    weekday_levels = np.select(weekday_conditions, [0.18, 0.31, 0.28, 0.42], default=0.24)
    weekend_levels = np.select(weekend_conditions, [0.16, 0.24, 0.29, 0.34], default=0.22)
    timeline["base_background_pu"] = np.where(timeline["is_weekend"], weekend_levels, weekday_levels)
    timeline["profile_block"] = np.where(
        timeline["is_weekend"],
        np.select(
            weekend_conditions,
            ["weekend_overnight", "weekend_morning", "weekend_daytime", "weekend_evening"],
            default="weekend_late",
        ),
        np.select(
            weekday_conditions,
            ["weekday_overnight", "weekday_morning", "weekday_daytime", "weekday_evening_peak"],
            default="weekday_late",
        ),
    )
    timeline["month_multiplier"] = timeline["month"].map(MONTHLY_BACKGROUND_MULTIPLIERS).astype(float)
    timeline["quarter_adjustment"] = timeline["minute"].map({0: -0.010, 15: 0.000, 30: 0.008, 45: 0.004}).astype(float)

    transformer_base = transformers[
        [
            "transformer_id",
            "transformer_name",
            "zone_id",
            "transformer_capacity_kw_assumed",
        ]
    ].copy()
    transformer_base["zone_background_multiplier"] = transformer_base["zone_id"].map(ZONE_BACKGROUND_MULTIPLIERS).fillna(1.0)

    background = timeline.merge(transformer_base, how="cross")
    background["background_load_pu"] = (
        background["base_background_pu"]
        * background["month_multiplier"]
        * background["zone_background_multiplier"]
        + background["quarter_adjustment"]
    ).clip(lower=0.12, upper=0.55)
    background["background_load_kw"] = (
        background["transformer_capacity_kw_assumed"] * background["background_load_pu"]
    ).round(3)
    background["assumption_version"] = "dundee_v1_deterministic_transformer_profile"
    background["assumption_notes"] = (
        "Synthetic transformer-level background load derived from time-of-day blocks, weekday/weekend effects, "
        "zone multiplier, and a mild seasonal multiplier."
    )
    return background[
        [
            "timestamp",
            "date",
            "year",
            "month",
            "weekday_name",
            "is_weekend",
            "hour",
            "quarter_hour_slot",
            "zone_id",
            "transformer_id",
            "transformer_name",
            "transformer_capacity_kw_assumed",
            "profile_block",
            "background_load_pu",
            "background_load_kw",
            "assumption_version",
            "assumption_notes",
        ]
    ]


def build_price_table() -> pd.DataFrame:
    """Build a deterministic system-wide TOU price table on the 15-minute time base."""

    time_index = pd.date_range(YEAR_START, YEAR_END, freq=f"{TIMEBASE_MINUTES}min")
    price = pd.DataFrame({"timestamp": time_index})
    price["date"] = price["timestamp"].dt.date.astype(str)
    price["year"] = price["timestamp"].dt.year.astype("int64")
    price["month"] = price["timestamp"].dt.month.astype("int64")
    price["weekday_name"] = price["timestamp"].dt.day_name()
    price["is_weekend"] = price["timestamp"].dt.dayofweek >= 5
    price["hour"] = price["timestamp"].dt.hour.astype("int64")
    price["minute"] = price["timestamp"].dt.minute.astype("int64")
    price["quarter_hour_slot"] = ((price["hour"] * 60) + price["minute"]) // TIMEBASE_MINUTES

    weekday_conditions = [
        price["hour"].between(0, 5),
        price["hour"].between(6, 15),
        price["hour"].between(16, 20),
    ]
    weekend_conditions = [
        price["hour"].between(0, 6),
        price["hour"].between(7, 15),
        price["hour"].between(16, 20),
    ]
    weekday_prices = np.select(weekday_conditions, [0.18, 0.24, 0.34], default=0.22)
    weekend_prices = np.select(weekend_conditions, [0.17, 0.21, 0.25], default=0.19)
    price["price_gbp_per_kwh"] = np.where(price["is_weekend"], weekend_prices, weekday_prices).round(4)
    price["tariff_block"] = np.where(
        price["is_weekend"],
        np.select(
            weekend_conditions,
            ["weekend_overnight", "weekend_daytime", "weekend_evening"],
            default="weekend_late",
        ),
        np.select(
            weekday_conditions,
            ["weekday_overnight", "weekday_shoulder", "weekday_peak"],
            default="weekday_late",
        ),
    )
    price["price_p_per_kwh"] = (price["price_gbp_per_kwh"] * 100).round(2)
    price["assumption_version"] = "dundee_v1_deterministic_tou"
    price["assumption_notes"] = "Synthetic Dundee-wide TOU tariff for simulator V1; not a live retail tariff."
    return price[
        [
            "timestamp",
            "date",
            "year",
            "month",
            "weekday_name",
            "is_weekend",
            "hour",
            "quarter_hour_slot",
            "tariff_block",
            "price_gbp_per_kwh",
            "price_p_per_kwh",
            "assumption_version",
            "assumption_notes",
        ]
    ]


def build_pv_profile() -> pd.DataFrame:
    """Build an optional normalized daylight-shaped PV profile."""

    time_index = pd.date_range(YEAR_START, YEAR_END, freq=f"{TIMEBASE_MINUTES}min")
    pv = pd.DataFrame({"timestamp": time_index})
    pv["date"] = pv["timestamp"].dt.date.astype(str)
    pv["year"] = pv["timestamp"].dt.year.astype("int64")
    pv["month"] = pv["timestamp"].dt.month.astype("int64")
    pv["hour"] = pv["timestamp"].dt.hour.astype("int64")
    pv["minute"] = pv["timestamp"].dt.minute.astype("int64")
    pv["quarter_hour_slot"] = ((pv["hour"] * 60) + pv["minute"]) // TIMEBASE_MINUTES
    pv["daylight_hours"] = pv["month"].map(PV_DAYLIGHT_HOURS).astype(float)
    pv["seasonal_peak_cf"] = pv["month"].map(PV_SEASONAL_PEAK).astype(float)

    hour_decimal = pv["hour"] + (pv["minute"] / 60.0)
    sunrise = 12.5 - (pv["daylight_hours"] / 2.0)
    sunset = 12.5 + (pv["daylight_hours"] / 2.0)
    daylight_position = (hour_decimal - sunrise) / (sunset - sunrise)
    daylight_shape = np.where(
        (daylight_position >= 0.0) & (daylight_position <= 1.0),
        np.sin(np.pi * daylight_position) ** 1.5,
        0.0,
    )
    pv["pv_capacity_factor"] = (daylight_shape * pv["seasonal_peak_cf"]).round(6)
    pv["pv_generation_kw_per_mw"] = (pv["pv_capacity_factor"] * 1000).round(3)
    pv["assumption_version"] = "dundee_v1_normalized_pv_profile"
    pv["assumption_notes"] = (
        "Optional normalized PV profile for simulator V1, expressed as capacity factor and kW per 1 MW installed PV."
    )
    return pv[
        [
            "timestamp",
            "date",
            "year",
            "month",
            "hour",
            "quarter_hour_slot",
            "pv_capacity_factor",
            "pv_generation_kw_per_mw",
            "assumption_version",
            "assumption_notes",
        ]
    ]


def write_replay_notes(
    params: dict[str, Any],
    dropped_summary: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write the Dundee replay methodology and assumption notes."""

    dropped_lines = ["- None."]
    if not dropped_summary.empty:
        dropped_lines = [
            f"- {int(row['request_year'])} / `{row['drop_reason']}`: {int(row['count'])}"
            for _, row in dropped_summary.iterrows()
        ]

    lines = [
        "# Dundee Request Replay Notes",
        "",
        "These Dundee replay requests are derived from the model-ready session table and mapped onto the simulator zone/transformer topology using 15-minute slot alignment.",
        "",
        "## Replay Construction",
        "- One replay request is generated per usable Dundee charging session in 2023 or 2024.",
        "- `arrival_ts` preserves the observed timestamp, while `arrival_slot` floors to the 15-minute simulator time base.",
        "- `latest_finish_ts` uses the observed approximate departure timestamp, while `latest_finish_slot` rounds that deadline up to the 15-minute time base.",
        "- `requested_energy_kwh` equals the observed delivered session energy from the model-ready dataset.",
        "- `requested_duration_minutes` starts from the technical minimum charging time at the observed connector limit and then uses a deterministic preference-based share of the remaining observed dwell slack.",
        "",
        "## Preference Heuristics",
        "- User preference modes are assigned deterministically via a SHA-256 hash bucket keyed by `session_id` and `connector_type`.",
        "- AC sessions use the heuristic distribution `closest 50% / cheapest 35% / fastest 15%`.",
        "- Rapid sessions use `closest 25% / cheapest 15% / fastest 60%`.",
        "- Ultra-rapid sessions use `closest 15% / cheapest 10% / fastest 75%`.",
        "- Charger type preference maps directly from connector type when known, otherwise `Any`.",
        "",
        "## Replay Priors Captured",
        f"- Arrival hour distribution: {len(params['arrival_distributions']['hour_share'])} hourly buckets.",
        f"- Weekday/weekend split: `{params['arrival_distributions']['weekday_type_share']}`.",
        f"- Month share: `{params['arrival_distributions']['month_share']}`.",
        f"- Zone request share: `{params['zone_level_demand_share']['request_share']}`.",
        "",
        "## Exogenous Tables",
        "- `background_load_15min.csv` is a transformer-level deterministic profile scaled by synthetic transformer capacity and adjusted by time of day, weekday/weekend, zone, and season.",
        "- `price_table_15min.csv` is a Dundee-wide deterministic TOU tariff in GBP/kWh on the same 15-minute time base.",
        "- `pv_profile_15min.csv` is an optional normalized daylight-shaped PV capacity-factor profile on the same time base.",
        "",
        "## Dropped Sessions",
    ]
    lines.extend(dropped_lines)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_markdown(
    replay: pd.DataFrame,
    dropped_summary: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write the Dundee replay QC summary in markdown."""

    year_counts = replay["request_year"].value_counts().sort_index()
    zone_counts = replay.groupby(["zone_id", "zone_name"], as_index=False).size().rename(columns={"size": "request_count"})
    station_counts = replay.groupby(["station_id", "station_name"], as_index=False).size().rename(columns={"size": "request_count"})
    station_counts = station_counts.sort_values(["request_count", "station_name"], ascending=[False, True], kind="stable")
    arrival_hour_share = replay["arrival_hour"].value_counts(normalize=True).sort_index().round(4)
    energy_summary = summarize_distribution(replay["requested_energy_kwh"])
    slack_summary = summarize_distribution(replay["slack_minutes"])

    lines = [
        "# Dundee Request Replay Summary",
        "",
        "## Request Counts By Year",
        "",
        "| year | request_count |",
        "| --- | ---: |",
    ]
    for request_year, count in year_counts.items():
        lines.append(f"| {int(request_year)} | {int(count)} |")

    lines.extend(
        [
            "",
            "## Requests By Zone",
            "",
            "| zone_id | zone_name | request_count |",
            "| --- | --- | ---: |",
        ]
    )
    for _, row in zone_counts.sort_values("request_count", ascending=False, kind="stable").iterrows():
        lines.append(f"| {row['zone_id']} | {row['zone_name']} | {int(row['request_count'])} |")

    lines.extend(
        [
            "",
            "## Requests By Station",
            "",
            "| station_id | station_name | request_count |",
            "| --- | --- | ---: |",
        ]
    )
    for _, row in station_counts.iterrows():
        lines.append(f"| {row['station_id']} | {row['station_name']} | {int(row['request_count'])} |")

    lines.extend(
        [
            "",
            "## Arrival Histogram Summary",
            "",
            "| arrival_hour | share |",
            "| --- | ---: |",
        ]
    )
    for hour, share in arrival_hour_share.items():
        lines.append(f"| {int(hour):02d} | {float(share):.4f} |")

    lines.extend(
        [
            "",
            "## Requested Energy Summary",
            "",
            "| metric | value |",
            "| --- | ---: |",
        ]
    )
    for metric, value in energy_summary.items():
        lines.append(f"| {metric} | {value} |")

    lines.extend(
        [
            "",
            "## Slack-Time Summary",
            "",
            "| metric | value |",
            "| --- | ---: |",
        ]
    )
    for metric, value in slack_summary.items():
        lines.append(f"| {metric} | {value} |")

    lines.extend(
        [
            "",
            "## Dropped Sessions",
            "",
            "| request_year | drop_reason | count |",
            "| --- | --- | ---: |",
        ]
    )
    if dropped_summary.empty:
        lines.append("| n/a | none | 0 |")
    else:
        for _, row in dropped_summary.iterrows():
            lines.append(f"| {int(row['request_year'])} | {row['drop_reason']} | {int(row['count'])} |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Build Dundee replay requests, priors, exogenous tables, and QC outputs."""

    args = build_parser().parse_args()
    configure_logging(args.log_level)

    output_paths = [
        args.request_replay_2023_csv,
        args.request_replay_2024_csv,
        args.request_generator_params_json,
        args.background_load_15min_csv,
        args.price_table_15min_csv,
        args.pv_profile_15min_csv,
        args.request_replay_notes_md,
        args.request_replay_summary_csv,
        args.request_replay_summary_md,
    ]
    ensure_output_dirs(output_paths)

    clean, model_ready, spatial_map, transformers, _zones = load_inputs(args)
    replay, dropped_model = build_replay_candidates(model_ready, spatial_map)
    dropped_summary = build_dropped_summary(clean, model_ready, dropped_model)

    replay_2023 = replay[replay["request_year"] == 2023].copy()
    replay_2024 = replay[replay["request_year"] == 2024].copy()
    replay_2023.to_csv(args.request_replay_2023_csv, index=False)
    replay_2024.to_csv(args.request_replay_2024_csv, index=False)

    params = build_request_generator_params(replay, dropped_summary, args.request_generator_params_json)

    background_load = build_background_load(transformers)
    background_load.to_csv(args.background_load_15min_csv, index=False)

    price_table = build_price_table()
    price_table.to_csv(args.price_table_15min_csv, index=False)

    pv_profile = build_pv_profile()
    pv_profile.to_csv(args.pv_profile_15min_csv, index=False)

    summary_rows = build_summary_rows(replay, dropped_summary)
    summary_rows.to_csv(args.request_replay_summary_csv, index=False)
    write_replay_notes(params, dropped_summary, args.request_replay_notes_md)
    write_summary_markdown(replay, dropped_summary, args.request_replay_summary_md)

    print(f"request_count_2023={len(replay_2023)}")
    print(f"request_count_2024={len(replay_2024)}")
    print(f"unique_stations_used={replay['station_id'].nunique()}")
    print(f"unique_zones_used={replay['zone_id'].nunique()}")
    for path in output_paths:
        print(path.as_posix())


if __name__ == "__main__":
    main()
