"""Build Dundee interactive maps and corrected daily-energy visual review assets."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import branca.colormap as cm
import folium
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from folium.plugins import MarkerCluster

LOGGER = logging.getLogger("dundee_visuals")

LATE_OCT_START = pd.Timestamp("2024-10-19")
LATE_OCT_END = pd.Timestamp("2024-10-28")
FIFTEEN_MINUTES = pd.Timedelta(minutes=15)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line interface."""

    parser = argparse.ArgumentParser(description="Build Dundee interactive maps and corrected daily-energy charts.")
    parser.add_argument("--clean-csv", type=Path, default=Path("data/interim/dundee_sessions_clean.csv"))
    parser.add_argument(
        "--model-ready-csv",
        type=Path,
        default=Path("data/interim/dundee_sessions_model_ready.csv"),
    )
    parser.add_argument("--station-master", type=Path, default=Path("data/processed/station_master.csv"))
    parser.add_argument("--station-locations", type=Path, default=Path("data/processed/station_locations.csv"))
    parser.add_argument(
        "--station-catalog-geojson",
        type=Path,
        default=Path("data/processed/station_catalog.geojson"),
    )
    parser.add_argument("--maps-dir", type=Path, default=Path("outputs/maps"))
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

    logging.basicConfig(level=getattr(logging, level.upper()), format="%(levelname)s %(name)s: %(message)s")


def ensure_parent_dirs(paths: list[Path]) -> None:
    """Create output parents if needed."""

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def apply_plot_style() -> None:
    """Set a consistent visual style for presentation charts."""

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


def load_clean_for_visuals(clean_csv: Path) -> pd.DataFrame:
    """Load the minimum Dundee clean fields needed for visual review."""

    frame = pd.read_csv(
        clean_csv,
        usecols=["session_id", "arrival_ts", "energy_kwh", "session_minutes"],
        parse_dates=["arrival_ts"],
    )
    frame["energy_kwh"] = pd.to_numeric(frame["energy_kwh"], errors="coerce")
    frame["session_minutes"] = pd.to_numeric(frame["session_minutes"], errors="coerce")
    return frame


def load_model_ready_for_visuals(model_ready_csv: Path) -> pd.DataFrame:
    """Load the minimum model-ready fields needed for reconstructed energy."""

    frame = pd.read_csv(
        model_ready_csv,
        usecols=["session_id", "arrival_ts", "approx_departure_ts", "energy_kwh"],
        parse_dates=["arrival_ts", "approx_departure_ts"],
    )
    frame["energy_kwh"] = pd.to_numeric(frame["energy_kwh"], errors="coerce")
    return frame


def load_station_map_data(station_master_path: Path, station_locations_path: Path, station_catalog_geojson: Path) -> pd.DataFrame:
    """Load and merge Dundee station map data."""

    if not station_catalog_geojson.exists():
        raise FileNotFoundError(f"Missing station catalog GeoJSON: {station_catalog_geojson}")
    station_master = pd.read_csv(station_master_path)
    station_locations = pd.read_csv(station_locations_path)
    stations = station_master.merge(
        station_locations[
            [
                "station_id",
                "latitude",
                "longitude",
                "location_source",
                "location_confidence",
                "needs_manual_review",
            ]
        ],
        on="station_id",
        how="left",
        suffixes=("", "_location"),
    )
    stations["needs_manual_review"] = stations["needs_manual_review"].astype(bool)
    stations = stations.dropna(subset=["latitude", "longitude"]).copy()
    return stations.sort_values(["station_name", "station_id"], kind="stable").reset_index(drop=True)


def compute_raw_daily_energy_2024(clean: pd.DataFrame) -> pd.DataFrame:
    """Compute raw daily delivered energy by arrival date for 2024."""

    raw = clean[(clean["arrival_ts"].dt.year == 2024) & clean["energy_kwh"].notna()].copy()
    raw["date"] = raw["arrival_ts"].dt.floor("D")
    daily = raw.groupby("date", as_index=False).agg(raw_energy_kwh=("energy_kwh", "sum"))
    full_range = pd.DataFrame({"date": pd.date_range("2024-01-01", "2024-12-31", freq="D")})
    return full_range.merge(daily, on="date", how="left").fillna({"raw_energy_kwh": 0.0})


def reconstruct_filtered_daily_energy_2024(model_ready: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct filtered daily energy by uniformly distributing session energy across 15-minute slots."""

    subset = model_ready[
        (model_ready["arrival_ts"] < "2025-01-01") & (model_ready["approx_departure_ts"] >= "2024-01-01")
    ].copy()
    subset["slot_start_ts"] = subset["arrival_ts"].dt.floor("15min")
    subset["slot_end_ts"] = subset["approx_departure_ts"].dt.ceil("15min") - FIFTEEN_MINUTES

    n_slots = (
        ((subset["slot_end_ts"] - subset["slot_start_ts"]) / FIFTEEN_MINUTES)
        .round()
        .astype("int64")
        + 1
    ).clip(lower=1)

    repeated_slot_start = np.repeat(subset["slot_start_ts"].to_numpy(dtype="datetime64[ns]"), n_slots)
    repeated_slot_energy = np.repeat((subset["energy_kwh"].to_numpy(dtype=float) / n_slots), n_slots)
    group_starts = np.repeat(np.cumsum(np.r_[0, n_slots[:-1]]), n_slots)
    offsets = np.arange(int(n_slots.sum()), dtype=np.int64) - group_starts
    slot_ts = repeated_slot_start + offsets * np.timedelta64(15, "m")

    slots = pd.DataFrame({"slot_ts": slot_ts, "slot_energy_kwh": repeated_slot_energy})
    slots = slots[(slots["slot_ts"] >= "2024-01-01") & (slots["slot_ts"] < "2025-01-01")].copy()
    slots["date"] = pd.to_datetime(slots["slot_ts"]).dt.floor("D")

    daily = slots.groupby("date", as_index=False).agg(reconstructed_energy_kwh=("slot_energy_kwh", "sum"))
    full_range = pd.DataFrame({"date": pd.date_range("2024-01-01", "2024-12-31", freq="D")})
    return full_range.merge(daily, on="date", how="left").fillna({"reconstructed_energy_kwh": 0.0})


def create_popup_html(row: pd.Series) -> str:
    """Build the required popup content for a Dundee station marker."""

    rows = [
        ("Station Name", row["station_name"]),
        ("Station ID", row["station_id"]),
        ("Postcode", row.get("postcode_mode", "")),
        ("Charge Points", int(row["cp_count_total"])),
        ("Connector Mix", row["connector_mix_total"]),
        ("Proxy Max Power (kW)", int(row["station_max_power_kw_proxy"])),
        ("Sessions Total", int(row["sessions_total"])),
    ]
    html_rows = "".join(
        f"<tr><th style='text-align:left;padding-right:8px;'>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    return f"<table>{html_rows}</table>"


def build_interactive_map(
    stations: pd.DataFrame,
    output_path: Path,
    title: str,
    color_column: str | None = None,
    color_caption: str | None = None,
) -> None:
    """Build and save a Folium map with MarkerCluster."""

    center = [stations["latitude"].mean(), stations["longitude"].mean()]
    fmap = folium.Map(location=center, zoom_start=12, control_scale=True, tiles=None)
    folium.TileLayer("CartoDB positron", name="CartoDB Positron", control=False).add_to(fmap)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(fmap)

    folium.map.Marker(
        center,
        icon=folium.DivIcon(html=f"<div style='font-size:14px;font-weight:700;color:#102a43'>{title}</div>"),
    ).add_to(fmap)

    marker_cluster = MarkerCluster(name="Dundee Stations").add_to(fmap)
    colormap = None
    if color_column is not None:
        min_value = float(stations[color_column].min())
        max_value = float(stations[color_column].max())
        if min_value == max_value:
            max_value = min_value + 1.0
        colormap = cm.linear.YlGnBu_09.scale(min_value, max_value)
        colormap.caption = color_caption or color_column
        colormap.add_to(fmap)

    for _, row in stations.iterrows():
        popup = folium.Popup(create_popup_html(row), max_width=360)
        tooltip = f"{row['station_name']} ({row['cp_count_total']} CPs)"
        color = "#0f766e" if colormap is None else colormap(float(row[color_column]))
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            weight=1,
            color="#102a43",
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=popup,
            tooltip=tooltip,
        ).add_to(marker_cluster)

    folium.LayerControl(collapsed=False).add_to(fmap)
    fmap.save(str(output_path))


def save_figure(fig: plt.Figure, path: Path) -> None:
    """Save a matplotlib figure."""

    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_raw_daily_energy_2024(raw_daily: pd.DataFrame, output_path: Path) -> None:
    """Plot raw daily delivered energy by arrival date for 2024."""

    window_mask = (raw_daily["date"] >= LATE_OCT_START) & (raw_daily["date"] <= LATE_OCT_END)
    colors = np.where(window_mask, "#dc2626", "#2563eb")

    fig, ax = plt.subplots(figsize=(16, 5))
    ax.bar(raw_daily["date"], raw_daily["raw_energy_kwh"], color=colors, width=1.0)
    ax.set_title("Dundee Raw Daily Delivered Energy in 2024")
    ax.set_xlabel("Arrival Date")
    ax.set_ylabel("Energy (kWh)")
    ax.text(
        0.01,
        1.02,
        "Energy is summed on session arrival date only; no redistribution over occupied time.",
        transform=ax.transAxes,
        fontsize=9,
        color="#486581",
    )
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.axvspan(LATE_OCT_START, LATE_OCT_END + pd.Timedelta(days=1), color="#fde68a", alpha=0.25)
    save_figure(fig, output_path)


def plot_daily_energy_comparison(
    comparison: pd.DataFrame,
    output_path: Path,
    raw_ratio: float,
    reconstructed_ratio: float,
) -> None:
    """Plot raw versus reconstructed filtered daily energy for 2024."""

    fig, ax = plt.subplots(figsize=(16, 6))
    ax.plot(comparison["date"], comparison["raw_energy_kwh"], color="#0f766e", linewidth=1.9, label="Raw daily energy")
    ax.plot(
        comparison["date"],
        comparison["reconstructed_energy_kwh"],
        color="#d97706",
        linewidth=1.8,
        label="Reconstructed filtered daily energy",
    )
    ax.axvspan(LATE_OCT_START, LATE_OCT_END + pd.Timedelta(days=1), color="#fde68a", alpha=0.25, label="Late-Oct review window")
    ax.set_title("Dundee Daily Energy Comparison for 2024")
    ax.set_xlabel("Date")
    ax.set_ylabel("Energy (kWh)")
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.legend(loc="upper left", ncol=2)
    ax.text(
        0.01,
        0.98,
        f"Late-Oct median / nearby baseline: raw = {raw_ratio:.2f}x, reconstructed = {reconstructed_ratio:.2f}x",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#bcccdc"},
    )
    save_figure(fig, output_path)


def analyze_late_october(raw_daily: pd.DataFrame, reconstructed_daily: pd.DataFrame, clean: pd.DataFrame) -> dict[str, float | int | bool]:
    """Analyze whether the late-October dip is present in raw versus reconstructed views."""

    comparison = raw_daily.merge(reconstructed_daily, on="date", how="outer").sort_values("date")
    review_window = (comparison["date"] >= LATE_OCT_START) & (comparison["date"] <= LATE_OCT_END)
    baseline_window = (
        (comparison["date"] >= pd.Timestamp("2024-10-01"))
        & (comparison["date"] <= pd.Timestamp("2024-11-15"))
        & (~review_window)
    )

    raw_window_median = float(comparison.loc[review_window, "raw_energy_kwh"].median())
    raw_baseline_median = float(comparison.loc[baseline_window, "raw_energy_kwh"].median())
    reconstructed_window_median = float(comparison.loc[review_window, "reconstructed_energy_kwh"].median())
    reconstructed_baseline_median = float(comparison.loc[baseline_window, "reconstructed_energy_kwh"].median())

    raw_ratio = raw_window_median / raw_baseline_median if raw_baseline_median else 0.0
    reconstructed_ratio = (
        reconstructed_window_median / reconstructed_baseline_median if reconstructed_baseline_median else 0.0
    )

    clean_window = clean[(clean["arrival_ts"] >= LATE_OCT_START) & (clean["arrival_ts"] < LATE_OCT_END + pd.Timedelta(days=1))]
    bad_duration_rows = int((clean_window["session_minutes"].isna() | (clean_window["session_minutes"] <= 0)).sum())
    total_rows = int(len(clean_window))

    return {
        "raw_window_median": round(raw_window_median, 3),
        "raw_baseline_median": round(raw_baseline_median, 3),
        "raw_ratio": round(raw_ratio, 3),
        "reconstructed_window_median": round(reconstructed_window_median, 3),
        "reconstructed_baseline_median": round(reconstructed_baseline_median, 3),
        "reconstructed_ratio": round(reconstructed_ratio, 3),
        "raw_has_dip": raw_ratio < 0.75,
        "reconstructed_has_dip": reconstructed_ratio < 0.75,
        "late_oct_rows": total_rows,
        "late_oct_bad_duration_rows": bad_duration_rows,
    }


def write_visual_review_notes(output_path: Path, analysis: dict[str, float | int | bool]) -> None:
    """Write a markdown note summarizing the Dundee visual review."""

    raw_has_dip = bool(analysis["raw_has_dip"])
    reconstructed_has_dip = bool(analysis["reconstructed_has_dip"])
    only_reconstructed = (not raw_has_dip) and reconstructed_has_dip

    lines = [
        "# Dundee Visual Review Notes",
        "",
        "## Late-October Check",
        "",
        f"- Late-October raw daily energy dip present: {'Yes' if raw_has_dip else 'No'}",
        f"- Late-October reconstructed filtered energy dip present: {'Yes' if reconstructed_has_dip else 'No'}",
        f"- Raw late-October median / nearby baseline median: {analysis['raw_ratio']:.3f}x",
        f"- Reconstructed late-October median / nearby baseline median: {analysis['reconstructed_ratio']:.3f}x",
        "",
        "## Interpretation",
        "",
    ]

    if only_reconstructed:
        lines.extend(
            [
                "- The late-October drop appears to be a preprocessing artifact rather than a real demand collapse.",
                "- Raw arrival-date energy remains normal in the late-October window, while reconstructed filtered energy falls sharply.",
                f"- In the same window, {analysis['late_oct_bad_duration_rows']:,} of {analysis['late_oct_rows']:,} clean rows have missing or nonpositive `session_minutes`, so they are excluded from the filtered reconstruction.",
            ]
        )
    else:
        lines.extend(
            [
                "- The late-October comparison does not cleanly support a preprocessing-artifact-only interpretation.",
                "- Review the underlying session duration and energy fields before using the reconstructed series in presentation material.",
            ]
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "- Use the raw daily delivered energy chart in the presentation when discussing real-world daily demand behavior.",
            "- Use the reconstructed filtered daily series only as a modeling-diagnostic chart, with an explicit caveat that it is sensitive to QC exclusions and duration quality.",
            "",
            "## Note on Yearly Charts",
            "",
            "- The yearly charts were not regenerated in this step.",
            "- If the existing yearly charts are reused in slides, annotate them with: `2021 = Jul-Dec` and `2025 = Jan-Aug`.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    """Run the Dundee interactive map and corrected daily-energy workflow."""

    args = build_parser().parse_args()
    configure_logging(args.log_level)
    apply_plot_style()

    map_paths = [
        args.maps_dir / "dundee_station_map_interactive.html",
        args.maps_dir / "dundee_station_map_interactive_by_cp_count.html",
        args.maps_dir / "dundee_station_map_interactive_by_sessions.html",
    ]
    raw_chart_path = args.figures_dir / "dundee_daily_raw_energy_2024_bar.png"
    comparison_chart_path = args.figures_dir / "dundee_daily_energy_2024_comparison.png"
    visual_review_notes_path = args.qc_dir / "dundee_visual_review_notes.md"
    ensure_parent_dirs(map_paths + [raw_chart_path, comparison_chart_path, visual_review_notes_path])

    clean = load_clean_for_visuals(args.clean_csv)
    model_ready = load_model_ready_for_visuals(args.model_ready_csv)
    stations = load_station_map_data(args.station_master, args.station_locations, args.station_catalog_geojson)

    build_interactive_map(stations, map_paths[0], title="Dundee Stations")
    build_interactive_map(
        stations,
        map_paths[1],
        title="Dundee Stations by Charge Point Count",
        color_column="cp_count_total",
        color_caption="Charge point count",
    )
    build_interactive_map(
        stations,
        map_paths[2],
        title="Dundee Stations by Sessions",
        color_column="sessions_total",
        color_caption="Sessions total",
    )

    raw_daily = compute_raw_daily_energy_2024(clean)
    reconstructed_daily = reconstruct_filtered_daily_energy_2024(model_ready)
    analysis = analyze_late_october(raw_daily, reconstructed_daily, clean)

    plot_raw_daily_energy_2024(raw_daily, raw_chart_path)
    comparison = raw_daily.merge(reconstructed_daily, on="date", how="outer").sort_values("date")
    plot_daily_energy_comparison(
        comparison,
        comparison_chart_path,
        raw_ratio=float(analysis["raw_ratio"]),
        reconstructed_ratio=float(analysis["reconstructed_ratio"]),
    )
    write_visual_review_notes(visual_review_notes_path, analysis)

    for map_path in map_paths:
        LOGGER.info("Wrote %s", map_path)
    LOGGER.info("Wrote %s", raw_chart_path)
    LOGGER.info("Wrote %s", comparison_chart_path)
    LOGGER.info("Wrote %s", visual_review_notes_path)
    LOGGER.info("Late-October raw ratio: %.3f", float(analysis["raw_ratio"]))
    LOGGER.info("Late-October reconstructed ratio: %.3f", float(analysis["reconstructed_ratio"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
