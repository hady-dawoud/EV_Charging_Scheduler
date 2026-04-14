"""Build Dundee QC summaries, a model-ready view, and presentation plots."""

from __future__ import annotations

import argparse
import logging
import math
import textwrap
from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LOGGER = logging.getLogger("dundee_qc")

CONNECTOR_POWER_KW = {
    "ac": 22.0,
    "rapid": 50.0,
    "ultra_rapid": 150.0,
}
POWER_TOLERANCE_MULTIPLIER = 1.25
FIFTEEN_MINUTES = pd.Timedelta(minutes=15)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description="Build Dundee QC outputs and EDA plots.")
    parser.add_argument("--clean-parquet", type=Path, default=Path("data/interim/dundee_sessions_clean.parquet"))
    parser.add_argument("--clean-csv", type=Path, default=Path("data/interim/dundee_sessions_clean.csv"))
    parser.add_argument("--station-master", type=Path, default=Path("data/processed/station_master.csv"))
    parser.add_argument("--chargepoint-master", type=Path, default=Path("data/processed/chargepoint_master.csv"))
    parser.add_argument("--station-locations", type=Path, default=Path("data/processed/station_locations.csv"))
    parser.add_argument(
        "--station-catalog-geojson",
        type=Path,
        default=Path("data/processed/station_catalog.geojson"),
    )
    parser.add_argument(
        "--model-ready-csv",
        type=Path,
        default=Path("data/interim/dundee_sessions_model_ready.csv"),
    )
    parser.add_argument(
        "--model-ready-parquet",
        type=Path,
        default=Path("data/interim/dundee_sessions_model_ready.parquet"),
    )
    parser.add_argument("--figures-dir", type=Path, default=Path("outputs/figures"))
    parser.add_argument("--qc-dir", type=Path, default=Path("outputs/qc"))
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def configure_logging(level: str) -> None:
    """Configure script logging."""

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(levelname)s %(name)s: %(message)s",
    )


def ensure_parent_dirs(paths: list[Path]) -> None:
    """Create parent directories for the provided paths."""

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def load_clean_sessions(parquet_path: Path, csv_path: Path) -> pd.DataFrame:
    """Load the canonical cleaned Dundee sessions."""

    if parquet_path.exists():
        LOGGER.info("Loading clean Dundee sessions from %s", parquet_path)
        frame = pd.read_parquet(parquet_path)
    elif csv_path.exists():
        LOGGER.info("Loading clean Dundee sessions from %s", csv_path)
        frame = pd.read_csv(csv_path, parse_dates=["arrival_ts", "departure_ts"])
    else:
        raise FileNotFoundError(f"Missing clean Dundee inputs: {parquet_path} and {csv_path}")

    text_columns = ["session_id", "station_name", "station_id", "cp_id", "connector_type", "postcode"]
    for column in text_columns:
        frame[column] = frame[column].astype("string").str.strip()
    frame["arrival_ts"] = pd.to_datetime(frame["arrival_ts"], errors="coerce")
    frame["departure_ts"] = pd.to_datetime(frame["departure_ts"], errors="coerce")
    frame["energy_kwh"] = pd.to_numeric(frame["energy_kwh"], errors="coerce")
    frame["session_minutes"] = pd.to_numeric(frame["session_minutes"], errors="coerce").astype("Int64")
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    return frame


def load_station_artifacts(
    station_master_path: Path,
    chargepoint_master_path: Path,
    station_locations_path: Path,
    station_catalog_geojson_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load station-layer artifacts and verify the GeoJSON exists."""

    if not station_catalog_geojson_path.exists():
        raise FileNotFoundError(f"Missing station catalog GeoJSON: {station_catalog_geojson_path}")
    station_master = pd.read_csv(station_master_path)
    chargepoint_master = pd.read_csv(chargepoint_master_path)
    station_locations = pd.read_csv(station_locations_path)
    station_locations["needs_manual_review"] = station_locations["needs_manual_review"].astype(bool)
    return station_master, chargepoint_master, station_locations


def assumed_connector_power(series: pd.Series) -> pd.Series:
    """Map connector types to assumed power, defaulting to AC power."""

    return series.map(CONNECTOR_POWER_KW).fillna(CONNECTOR_POWER_KW["ac"]).astype(float)


def add_qc_flags(clean_sessions: pd.DataFrame) -> pd.DataFrame:
    """Add modeling and QC helper columns without mutating the clean source."""

    enriched = clean_sessions.copy()
    enriched["assumed_connector_limit_kw"] = assumed_connector_power(enriched["connector_type"])
    enriched["connector_limit_with_tolerance_kw"] = (
        enriched["assumed_connector_limit_kw"] * POWER_TOLERANCE_MULTIPLIER
    )

    duration_hours = enriched["session_minutes"].astype("Float64") / 60.0
    enriched["implied_average_power_kw"] = np.where(
        duration_hours.notna() & (duration_hours > 0) & enriched["energy_kwh"].notna(),
        enriched["energy_kwh"] / duration_hours,
        np.nan,
    )
    enriched["approx_departure_ts"] = enriched["arrival_ts"] + pd.to_timedelta(
        enriched["session_minutes"].astype("Float64"),
        unit="m",
    )

    cp_station_count = (
        enriched.loc[enriched["cp_id"].notna()]
        .groupby("cp_id", dropna=False)["station_id"]
        .nunique(dropna=True)
        .rename("cp_station_count")
    )
    enriched = enriched.merge(cp_station_count, on="cp_id", how="left")
    enriched["cp_station_count"] = enriched["cp_station_count"].fillna(0).astype(int)

    enriched["flag_missing_energy"] = enriched["energy_kwh"].isna()
    enriched["flag_missing_departure"] = enriched["departure_ts"].isna()
    enriched["flag_nonpositive_duration"] = enriched["session_minutes"].notna() & (
        enriched["session_minutes"] <= 0
    )
    enriched["flag_nonpositive_energy"] = enriched["energy_kwh"].notna() & (
        enriched["energy_kwh"] <= 0
    )
    enriched["flag_extreme_duration_gt_24h"] = enriched["session_minutes"].notna() & (
        enriched["session_minutes"] > (24 * 60)
    )
    enriched["flag_extreme_duration_gt_48h"] = enriched["session_minutes"].notna() & (
        enriched["session_minutes"] > (48 * 60)
    )
    enriched["flag_implied_power_above_connector_limit"] = (
        pd.Series(enriched["implied_average_power_kw"]).notna()
        & (
            pd.Series(enriched["implied_average_power_kw"])
            > enriched["connector_limit_with_tolerance_kw"]
        )
    )
    enriched["flag_cp_id_multi_station"] = enriched["cp_station_count"] > 1
    return enriched


def build_model_ready(enriched: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Filter the QC-enriched dataset into a model-ready view."""

    valid_arrival = enriched["arrival_ts"].notna()
    valid_duration = enriched["session_minutes"].notna() & (enriched["session_minutes"] > 0)
    valid_energy = enriched["energy_kwh"].notna() & (enriched["energy_kwh"] > 0)
    valid_power = ~enriched["flag_implied_power_above_connector_limit"]

    keep_mask = valid_arrival & valid_duration & valid_energy & valid_power
    model_ready = enriched.loc[keep_mask].copy().reset_index(drop=True)

    exclusion_counts = {
        "excluded_missing_arrival_ts": int((~valid_arrival).sum()),
        "excluded_missing_or_nonpositive_session_minutes": int((~valid_duration).sum()),
        "excluded_missing_or_nonpositive_energy": int((~valid_energy).sum()),
        "excluded_implied_power_above_connector_limit": int((~valid_power).sum()),
    }
    return model_ready, exclusion_counts


def reconstruct_load_15min(model_ready: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct a 15-minute load table from kept sessions."""

    sessions = model_ready.copy()
    sessions["slot_start_ts"] = sessions["arrival_ts"].dt.floor("15min")
    sessions["slot_end_ts"] = sessions["approx_departure_ts"].dt.ceil("15min") - FIFTEEN_MINUTES
    n_slots = (
        ((sessions["slot_end_ts"] - sessions["slot_start_ts"]) / FIFTEEN_MINUTES)
        .round()
        .astype("int64")
        + 1
    )
    n_slots = np.maximum(n_slots, 1)

    total_slots = int(n_slots.sum())
    LOGGER.info("Reconstructing %s occupied 15-minute slots from kept Dundee sessions.", f"{total_slots:,}")

    repeated_slot_start = np.repeat(
        sessions["slot_start_ts"].to_numpy(dtype="datetime64[ns]"),
        n_slots,
    )
    repeated_slot_energy = np.repeat(
        (sessions["energy_kwh"].to_numpy(dtype=float) / n_slots),
        n_slots,
    )
    group_starts = np.repeat(np.cumsum(np.r_[0, n_slots[:-1]]), n_slots)
    offsets = np.arange(total_slots, dtype=np.int64) - group_starts
    slot_ts = repeated_slot_start + offsets * np.timedelta64(15, "m")

    load_15min = (
        pd.DataFrame({"slot_ts": slot_ts, "slot_energy_kwh": repeated_slot_energy})
        .groupby("slot_ts", as_index=False)
        .agg(slot_energy_kwh=("slot_energy_kwh", "sum"))
        .sort_values("slot_ts", kind="stable")
        .reset_index(drop=True)
    )
    load_15min["slot_kw"] = load_15min["slot_energy_kwh"] / 0.25
    load_15min["date"] = load_15min["slot_ts"].dt.date.astype("string")
    load_15min["year"] = load_15min["slot_ts"].dt.year
    load_15min["hour"] = load_15min["slot_ts"].dt.hour
    return load_15min


def apply_plot_style() -> None:
    """Set a clean presentation-ready plotting style."""

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#f7fafc",
            "axes.edgecolor": "#1f2933",
            "axes.labelcolor": "#1f2933",
            "text.color": "#1f2933",
            "xtick.color": "#1f2933",
            "ytick.color": "#1f2933",
            "grid.color": "#d9e2ec",
            "font.size": 10,
            "axes.titleweight": "bold",
        }
    )


def save_figure(fig: plt.Figure, path: Path) -> None:
    """Save a matplotlib figure."""

    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_sessions_by_year(model_ready: pd.DataFrame, output_path: Path) -> None:
    """Plot Dundee session counts by year."""

    summary = (
        model_ready.groupby("year", dropna=False)
        .agg(sessions=("session_id", "count"))
        .reset_index()
        .sort_values("year")
    )
    x_positions = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(x_positions, summary["sessions"], color="#0f766e")
    ax.set_title("Dundee Charging Sessions by Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Sessions")
    ax.set_xticks(x_positions, summary["year"].astype(int).astype(str))
    ax.bar_label(bars, fmt="%.0f", padding=3, fontsize=9)
    save_figure(fig, output_path)


def plot_energy_by_year(model_ready: pd.DataFrame, output_path: Path) -> None:
    """Plot Dundee delivered energy by year."""

    summary = (
        model_ready.groupby("year", dropna=False)
        .agg(energy_kwh=("energy_kwh", "sum"))
        .reset_index()
        .sort_values("year")
    )
    x_positions = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(x_positions, summary["energy_kwh"], color="#f59e0b")
    ax.set_title("Dundee Delivered Energy by Year")
    ax.set_xlabel("Year")
    ax.set_ylabel("Energy (kWh)")
    ax.set_xticks(x_positions, summary["year"].astype(int).astype(str))
    ax.bar_label(bars, fmt="%.0f", padding=3, fontsize=9)
    save_figure(fig, output_path)


def plot_daily_energy_2024(load_15min: pd.DataFrame, output_path: Path) -> None:
    """Plot total reconstructed daily energy for 2024."""

    daily = (
        load_15min.loc[load_15min["year"] == 2024]
        .groupby("date", dropna=False)
        .agg(energy_kwh=("slot_energy_kwh", "sum"))
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.bar(daily["date"], daily["energy_kwh"], width=1.0, color="#2563eb")
    ax.set_title("Dundee Reconstructed Daily Energy in 2024")
    ax.set_xlabel("Date")
    ax.set_ylabel("Energy (kWh)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.tick_params(axis="x", rotation=0)
    save_figure(fig, output_path)


def plot_hourly_load_profile(load_15min: pd.DataFrame, output_path: Path) -> None:
    """Plot the average reconstructed load by hour of day."""

    hourly = (
        load_15min.groupby("hour", dropna=False)
        .agg(avg_load_kw=("slot_kw", "mean"))
        .reset_index()
        .sort_values("hour")
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(hourly["hour"], hourly["avg_load_kw"], color="#7c3aed")
    ax.set_title("Dundee Average Reconstructed Load by Hour of Day")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Average Load (kW)")
    ax.set_xticks(range(24))
    save_figure(fig, output_path)


def build_map_labels(stations: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Split numbered station labels into two columns for the map legend."""

    labels = [
        f"{int(row.map_index):02d} {textwrap.shorten(str(row.station_name), width=36, placeholder='...')}"
        for row in stations.itertuples(index=False)
    ]
    midpoint = math.ceil(len(labels) / 2)
    return labels[:midpoint], labels[midpoint:]


def render_station_map(
    stations: pd.DataFrame,
    output_path: Path,
    title: str,
    color_column: str | None = None,
    color_label: str | None = None,
) -> str:
    """Render a fallback Dundee station map using lon/lat scatter plotting."""

    method = "fallback_scatter"
    fig = plt.figure(figsize=(16, 10))
    grid = fig.add_gridspec(1, 2, width_ratios=[2.4, 1.6])
    ax = fig.add_subplot(grid[0, 0])
    legend_ax = fig.add_subplot(grid[0, 1])
    legend_ax.axis("off")

    plot_data = stations.sort_values("map_index", kind="stable")
    if color_column is None:
        ax.scatter(
            plot_data["longitude"],
            plot_data["latitude"],
            s=170,
            c="#0f766e",
            edgecolors="#102a43",
            linewidths=0.8,
            alpha=0.95,
        )
    else:
        scatter = ax.scatter(
            plot_data["longitude"],
            plot_data["latitude"],
            s=170,
            c=plot_data[color_column],
            cmap="viridis",
            edgecolors="#102a43",
            linewidths=0.8,
            alpha=0.95,
        )
        cbar = fig.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(color_label or color_column)

    for row in plot_data.itertuples(index=False):
        ax.text(
            row.longitude,
            row.latitude,
            str(int(row.map_index)),
            ha="center",
            va="center",
            fontsize=8,
            color="white",
            fontweight="bold",
        )

    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal", adjustable="datalim")

    labels_left, labels_right = build_map_labels(plot_data)
    legend_ax.text(0.02, 0.98, "\n".join(labels_left), va="top", ha="left", fontsize=8.5)
    legend_ax.text(0.52, 0.98, "\n".join(labels_right), va="top", ha="left", fontsize=8.5)
    legend_ax.set_title("Station Key", loc="left", fontsize=11, fontweight="bold")

    save_figure(fig, output_path)
    return method


def create_plots(
    model_ready: pd.DataFrame,
    load_15min: pd.DataFrame,
    station_master: pd.DataFrame,
    station_locations: pd.DataFrame,
    figures_dir: Path,
) -> tuple[list[Path], str]:
    """Create all required Dundee presentation plots."""

    figures_dir.mkdir(parents=True, exist_ok=True)
    plot_paths = [
        figures_dir / "dundee_demand_growth_sessions_by_year.png",
        figures_dir / "dundee_energy_by_year_kwh.png",
        figures_dir / "dundee_daily_energy_2024_bar.png",
        figures_dir / "dundee_hourly_load_profile_bar.png",
        figures_dir / "dundee_station_map.png",
        figures_dir / "dundee_station_map_colored_by_cp_count.png",
        figures_dir / "dundee_station_map_colored_by_sessions.png",
    ]

    plot_sessions_by_year(model_ready, plot_paths[0])
    plot_energy_by_year(model_ready, plot_paths[1])
    plot_daily_energy_2024(load_15min, plot_paths[2])
    plot_hourly_load_profile(load_15min, plot_paths[3])

    stations_for_map = (
        station_master.merge(
            station_locations[["station_id", "needs_manual_review"]],
            on="station_id",
            how="left",
        )
        .sort_values(["station_name", "station_id"], kind="stable")
        .reset_index(drop=True)
    )
    stations_for_map["map_index"] = np.arange(1, len(stations_for_map) + 1)

    map_method = render_station_map(
        stations_for_map,
        plot_paths[4],
        title="Dundee Station Map",
    )
    render_station_map(
        stations_for_map,
        plot_paths[5],
        title="Dundee Station Map Colored by Charge Point Count",
        color_column="cp_count_total",
        color_label="Charge point count",
    )
    render_station_map(
        stations_for_map,
        plot_paths[6],
        title="Dundee Station Map Colored by Session Count",
        color_column="sessions_total",
        color_label="Session count",
    )
    return plot_paths, map_method


def build_quality_summary_rows(
    clean_sessions: pd.DataFrame,
    model_ready: pd.DataFrame,
    enriched: pd.DataFrame,
    station_master: pd.DataFrame,
    exclusion_counts: dict[str, int],
    map_method: str,
) -> pd.DataFrame:
    """Build a flat QC summary table for CSV export."""

    rows: list[dict[str, Any]] = [
        {
            "section": "overview",
            "rank": "",
            "item": "total_rows_clean",
            "value": int(len(clean_sessions)),
            "station_id": "",
            "station_name": "",
            "notes": "",
        },
        {
            "section": "overview",
            "rank": "",
            "item": "total_rows_model_ready",
            "value": int(len(model_ready)),
            "station_id": "",
            "station_name": "",
            "notes": "",
        },
        {
            "section": "overview",
            "rank": "",
            "item": "rows_removed",
            "value": int(len(clean_sessions) - len(model_ready)),
            "station_id": "",
            "station_name": "",
            "notes": "Rows may satisfy multiple exclusion conditions below.",
        },
    ]

    flag_columns = [
        "flag_missing_energy",
        "flag_missing_departure",
        "flag_nonpositive_duration",
        "flag_nonpositive_energy",
        "flag_extreme_duration_gt_24h",
        "flag_extreme_duration_gt_48h",
        "flag_implied_power_above_connector_limit",
        "flag_cp_id_multi_station",
    ]
    for flag_column in flag_columns:
        rows.append(
            {
                "section": "qc_flags",
                "rank": "",
                "item": flag_column,
                "value": int(enriched[flag_column].sum()),
                "station_id": "",
                "station_name": "",
                "notes": "",
            }
        )

    for item, value in exclusion_counts.items():
        rows.append(
            {
                "section": "model_filter",
                "rank": "",
                "item": item,
                "value": int(value),
                "station_id": "",
                "station_name": "",
                "notes": "Counts are not mutually exclusive.",
            }
        )

    top_sessions = (
        station_master[["station_id", "station_name", "sessions_total", "cp_count_total"]]
        .sort_values(["sessions_total", "cp_count_total", "station_name"], ascending=[False, False, True])
        .head(10)
        .reset_index(drop=True)
    )
    for idx, row in top_sessions.iterrows():
        rows.append(
            {
                "section": "top_stations_by_sessions",
                "rank": idx + 1,
                "item": "sessions_total",
                "value": int(row["sessions_total"]),
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "notes": "",
            }
        )

    top_cp = (
        station_master[["station_id", "station_name", "cp_count_total", "sessions_total"]]
        .sort_values(["cp_count_total", "sessions_total", "station_name"], ascending=[False, False, True])
        .head(10)
        .reset_index(drop=True)
    )
    for idx, row in top_cp.iterrows():
        rows.append(
            {
                "section": "top_stations_by_cp_count_total",
                "rank": idx + 1,
                "item": "cp_count_total",
                "value": int(row["cp_count_total"]),
                "station_id": row["station_id"],
                "station_name": row["station_name"],
                "notes": "",
            }
        )

    conflict_cp_ids = (
        enriched.loc[enriched["flag_cp_id_multi_station"], "cp_id"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    suspicious_notes = [
        (
            "cp_id_multi_station_conflicts",
            f"{len(conflict_cp_ids)} conflicting cp_id values detected.",
            ", ".join(conflict_cp_ids) if conflict_cp_ids else "None",
        ),
        (
            "extreme_duration_gt_48h",
            f"{int(enriched['flag_extreme_duration_gt_48h'].sum())} rows exceed 48 hours.",
            "Long parking behavior may merit a later business rule review.",
        ),
        (
            "missing_departure_rows",
            f"{int(enriched['flag_missing_departure'].sum())} rows have missing departure timestamps.",
            "These rows are excluded from the model-ready view only when duration is also missing or invalid.",
        ),
        (
            "map_rendering_method",
            map_method,
            "geopandas/contextily were unavailable, so plots use a deterministic lon/lat scatter fallback.",
        ),
    ]
    for idx, (item, value, notes) in enumerate(suspicious_notes, start=1):
        rows.append(
            {
                "section": "suspicious_notes",
                "rank": idx,
                "item": item,
                "value": value,
                "station_id": "",
                "station_name": "",
                "notes": notes,
            }
        )

    return pd.DataFrame(rows)


def write_quality_summary_markdown(
    clean_sessions: pd.DataFrame,
    model_ready: pd.DataFrame,
    enriched: pd.DataFrame,
    station_master: pd.DataFrame,
    exclusion_counts: dict[str, int],
    plot_paths: list[Path],
    map_method: str,
    output_path: Path,
) -> None:
    """Write a presentation-friendly markdown QC summary."""

    flag_columns = [
        "flag_missing_energy",
        "flag_missing_departure",
        "flag_nonpositive_duration",
        "flag_nonpositive_energy",
        "flag_extreme_duration_gt_24h",
        "flag_extreme_duration_gt_48h",
        "flag_implied_power_above_connector_limit",
        "flag_cp_id_multi_station",
    ]
    flag_table = pd.DataFrame(
        {
            "flag": flag_columns,
            "count": [int(enriched[column].sum()) for column in flag_columns],
        }
    )
    top_sessions = (
        station_master[["station_name", "sessions_total", "cp_count_total"]]
        .sort_values(["sessions_total", "cp_count_total", "station_name"], ascending=[False, False, True])
        .head(10)
    )
    top_cp = (
        station_master[["station_name", "cp_count_total", "sessions_total"]]
        .sort_values(["cp_count_total", "sessions_total", "station_name"], ascending=[False, False, True])
        .head(10)
    )
    conflict_cp_ids = (
        enriched.loc[enriched["flag_cp_id_multi_station"], "cp_id"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    content = "\n".join(
        [
            "# Dundee Quality Summary",
            "",
            "## Overview",
            "",
            f"- Total rows in clean file: {len(clean_sessions):,}",
            f"- Total rows in model_ready file: {len(model_ready):,}",
            f"- Number removed: {len(clean_sessions) - len(model_ready):,}",
            "",
            "## Model Filter Counts",
            "",
            f"- Missing arrival timestamps: {exclusion_counts['excluded_missing_arrival_ts']:,}",
            f"- Missing or nonpositive session minutes: {exclusion_counts['excluded_missing_or_nonpositive_session_minutes']:,}",
            f"- Missing or nonpositive energy: {exclusion_counts['excluded_missing_or_nonpositive_energy']:,}",
            f"- Implied power above connector tolerance: {exclusion_counts['excluded_implied_power_above_connector_limit']:,}",
            "",
            "Counts above are not mutually exclusive.",
            "",
            "## QC Flag Counts",
            "",
            "```text",
            flag_table.to_string(index=False),
            "```",
            "",
            "## Top Stations By Sessions",
            "",
            "```text",
            top_sessions.to_string(index=False),
            "```",
            "",
            "## Top Stations By Charge Point Count",
            "",
            "```text",
            top_cp.to_string(index=False),
            "```",
            "",
            "## Suspicious Records Notes",
            "",
            f"- cp_id values attached to multiple station_ids: {len(conflict_cp_ids)}",
            f"- Conflicting cp_id list: {', '.join(conflict_cp_ids) if conflict_cp_ids else 'None'}",
            f"- Rows with durations above 24 hours: {int(enriched['flag_extreme_duration_gt_24h'].sum()):,}",
            f"- Rows with durations above 48 hours: {int(enriched['flag_extreme_duration_gt_48h'].sum()):,}",
            f"- Rows with missing departure timestamps: {int(enriched['flag_missing_departure'].sum()):,}",
            f"- Map rendering method: {map_method}",
            "",
            "## Generated Plots",
            "",
            *[f"- `{path.as_posix()}`" for path in plot_paths],
            "",
        ]
    )
    output_path.write_text(content, encoding="utf-8")


def write_model_ready(model_ready: pd.DataFrame, csv_path: Path, parquet_path: Path) -> None:
    """Write the filtered model-ready dataset."""

    model_ready.to_csv(csv_path, index=False)
    model_ready.to_parquet(parquet_path, index=False)


def main() -> int:
    """Run the Dundee QC, EDA, and visualization workflow."""

    args = build_parser().parse_args()
    configure_logging(args.log_level)
    apply_plot_style()

    output_paths = [
        args.model_ready_csv,
        args.model_ready_parquet,
        args.qc_dir / "dundee_quality_summary.csv",
        args.qc_dir / "dundee_quality_summary.md",
        args.figures_dir / "dundee_demand_growth_sessions_by_year.png",
        args.figures_dir / "dundee_energy_by_year_kwh.png",
        args.figures_dir / "dundee_daily_energy_2024_bar.png",
        args.figures_dir / "dundee_hourly_load_profile_bar.png",
        args.figures_dir / "dundee_station_map.png",
        args.figures_dir / "dundee_station_map_colored_by_cp_count.png",
        args.figures_dir / "dundee_station_map_colored_by_sessions.png",
    ]
    ensure_parent_dirs(output_paths)

    clean_sessions = load_clean_sessions(args.clean_parquet, args.clean_csv)
    station_master, chargepoint_master, station_locations = load_station_artifacts(
        args.station_master,
        args.chargepoint_master,
        args.station_locations,
        args.station_catalog_geojson,
    )
    _ = chargepoint_master

    enriched = add_qc_flags(clean_sessions)
    model_ready, exclusion_counts = build_model_ready(enriched)
    load_15min = reconstruct_load_15min(model_ready)

    write_model_ready(model_ready, args.model_ready_csv, args.model_ready_parquet)
    plot_paths, map_method = create_plots(
        model_ready,
        load_15min,
        station_master,
        station_locations,
        args.figures_dir,
    )

    quality_summary = build_quality_summary_rows(
        clean_sessions=clean_sessions,
        model_ready=model_ready,
        enriched=enriched,
        station_master=station_master,
        exclusion_counts=exclusion_counts,
        map_method=map_method,
    )
    quality_summary_csv = args.qc_dir / "dundee_quality_summary.csv"
    quality_summary_md = args.qc_dir / "dundee_quality_summary.md"
    quality_summary.to_csv(quality_summary_csv, index=False)
    write_quality_summary_markdown(
        clean_sessions=clean_sessions,
        model_ready=model_ready,
        enriched=enriched,
        station_master=station_master,
        exclusion_counts=exclusion_counts,
        plot_paths=plot_paths,
        map_method=map_method,
        output_path=quality_summary_md,
    )

    LOGGER.info("Wrote %s", args.model_ready_csv)
    LOGGER.info("Wrote %s", args.model_ready_parquet)
    LOGGER.info("Wrote %s", quality_summary_csv)
    LOGGER.info("Wrote %s", quality_summary_md)
    for plot_path in plot_paths:
        LOGGER.info("Wrote %s", plot_path)

    excluded_rows = len(clean_sessions) - len(model_ready)
    LOGGER.info("Model-ready rows: %s", f"{len(model_ready):,}")
    LOGGER.info("Excluded rows: %s", f"{excluded_rows:,}")
    LOGGER.info("Map rendering method: %s", map_method)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
