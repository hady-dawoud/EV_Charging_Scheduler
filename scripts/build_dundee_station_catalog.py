"""Build Dundee station, chargepoint, and location catalogs from cleaned sessions.

This script is intentionally Dundee-only. It reads the cleaned Dundee session
dataset, aggregates one row per station and charge point, and attaches a frozen
deterministic location seed for V1 mapping work.

Location strategy:
- Prefer exact named-feature matches from OpenStreetMap when the site name is
  directly identifiable.
- Fall back to road/square matches when the charger is clearly tied to a named
  street or civic square.
- Fall back to frozen postcode centroids when only the station postcode could
  be resolved deterministically.
- Use shared-site mappings for a small number of stations whose dataset name
  maps to the same physical venue.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger("dundee_station_catalog")

POWER_KW_BY_CONNECTOR = {
    "ac": 22,
    "rapid": 50,
    "ultra_rapid": 150,
}

LOCATION_SEED_ROWS: list[dict[str, Any]] = [
    {
        "station_id": "alexander_street_dundee",
        "latitude": 56.469369,
        "longitude": -2.968713,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using dataset postcode centroid; station name and street lookup do not align cleanly.",
    },
    {
        "station_id": "balmerino_road",
        "latitude": 56.4808461,
        "longitude": -2.9100671,
        "location_source": "osm_road_match",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Matched to Balmerino Road in Dundee using the station road name and postcode context.",
    },
    {
        "station_id": "caird_avenue",
        "latitude": 56.4763808,
        "longitude": -2.9783902,
        "location_source": "osm_road_match",
        "location_confidence": "low",
        "needs_manual_review": True,
        "notes": "No postcode in the dataset; using the first deterministic Caird Avenue road match in Dundee.",
    },
    {
        "station_id": "camperdown_country_park",
        "latitude": 56.4810593,
        "longitude": -3.0377513,
        "location_source": "osm_named_feature",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Matched to the named Camperdown Country Park feature rather than a charger-specific marker.",
    },
    {
        "station_id": "clepington_road_4th_hub",
        "latitude": 56.478799,
        "longitude": -2.985238,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the resolved Dundee postcode centroid for the Clepington Road hub.",
    },
    {
        "station_id": "coldside_nursery",
        "latitude": 56.4757059,
        "longitude": -2.9785033,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "craigowen_road",
        "latitude": 56.473731,
        "longitude": -3.035025,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the resolved Dundee postcode centroid for Craigowen Road.",
    },
    {
        "station_id": "dawson_park_broughty_ferry",
        "latitude": 56.472647,
        "longitude": -2.898492,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the dataset postcode centroid for Dawson Park, Broughty Ferry.",
    },
    {
        "station_id": "derby_street",
        "latitude": 56.472804,
        "longitude": -2.959175,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Street-name search was ambiguous; using the dataset postcode centroid instead.",
    },
    {
        "station_id": "deveron_terrace",
        "latitude": 56.4684347,
        "longitude": -3.0478484,
        "location_source": "osm_road_match",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Matched to the named Deveron Terrace road in Dundee.",
    },
    {
        "station_id": "dock_street_dundee",
        "latitude": 56.4603122,
        "longitude": -2.9665487,
        "location_source": "osm_road_match",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "douglas_community_library",
        "latitude": 56.4793848,
        "longitude": -2.9050982,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "dundee_house_depot_north_lindsay_street_dundee",
        "latitude": 56.4606745,
        "longitude": -2.9755925,
        "location_source": "osm_road_match",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Matched to North Lindsay Street because the exact depot was not exposed as a named map feature.",
    },
    {
        "station_id": "dundee_ice_arena_dundee",
        "latitude": 56.4816435,
        "longitude": -3.0248131,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "dundee_railway_station",
        "latitude": 56.4576613,
        "longitude": -2.969612,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "dundee_taybridge_rail_station_south_union_street_dundee",
        "latitude": 56.4576613,
        "longitude": -2.969612,
        "location_source": "manual_shared_site",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Mapped to the Dundee Railway Station site because the dataset station name points to the same South Union Street rail venue.",
    },
    {
        "station_id": "eastern_primary_school",
        "latitude": 56.4698114,
        "longitude": -2.8797259,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "gellatly_street_car_park_dundee",
        "latitude": 56.461363,
        "longitude": -2.9662611,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "greenmarket_150kw_bus_charger",
        "latitude": 56.457522,
        "longitude": -2.969515,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the Greenmarket postcode centroid; this station should be reviewed against any future charger-specific site map.",
    },
    {
        "station_id": "greenmarket_multi_storey_car_park_dundee",
        "latitude": 56.4565851,
        "longitude": -2.9734373,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "housing_office_east_midmill_road_dundee",
        "latitude": 56.483461,
        "longitude": -2.934227,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the resolved Midmill Road postcode centroid.",
    },
    {
        "station_id": "lochee_charging_hub_aimer_square_dundee",
        "latitude": 56.4717313,
        "longitude": -3.0099183,
        "location_source": "osm_square_match",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "menzieshill_community_centre",
        "latitude": 56.4679439,
        "longitude": -3.0394642,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "michelin_scotland_innovation_park",
        "latitude": 56.4849476,
        "longitude": -2.8954416,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "mill_o_mains_primary_school",
        "latitude": 56.49305,
        "longitude": -2.958646,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the resolved school postcode centroid.",
    },
    {
        "station_id": "nethergate_dundee",
        "latitude": 56.457336,
        "longitude": -2.978272,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the dataset postcode centroid for Nethergate.",
    },
    {
        "station_id": "olympia_hub",
        "latitude": 56.4640377,
        "longitude": -2.9632878,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "olympia_multi_storey_car_park_dundee",
        "latitude": 56.463861,
        "longitude": -2.963022,
        "location_source": "postcodes_io_centroid",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Using the Olympia postcode centroid; this row should be reviewed if a car-park polygon or charger-specific marker becomes available.",
    },
    {
        "station_id": "orleans_place_dundee",
        "latitude": 56.467139,
        "longitude": -3.039,
        "location_source": "manual_street_postcode_match",
        "location_confidence": "medium",
        "needs_manual_review": True,
        "notes": "Dataset postcode was missing; using the Orleans Place Dundee street/postcode match captured during manual lookup.",
    },
    {
        "station_id": "princes_street_charging_hub_dundee",
        "latitude": 56.4659398,
        "longitude": -2.962377,
        "location_source": "osm_road_match",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "queen_street_charging_hub_dundee",
        "latitude": 56.4678511,
        "longitude": -2.8724124,
        "location_source": "osm_road_match",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "rpc_dundee",
        "latitude": 56.4820818,
        "longitude": -2.9559291,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "south_tay_street_car_club_public",
        "latitude": 56.458878,
        "longitude": -2.9769227,
        "location_source": "osm_road_match",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "trades_lane_dundee",
        "latitude": 56.4631551,
        "longitude": -2.9662628,
        "location_source": "osm_road_match",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
    {
        "station_id": "whitfield_centre_lothian_crescent_dundee",
        "latitude": 56.4898723,
        "longitude": -2.9163685,
        "location_source": "osm_named_feature",
        "location_confidence": "high",
        "needs_manual_review": False,
        "notes": "",
    },
]


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line interface."""

    parser = argparse.ArgumentParser(description="Build Dundee station and location catalogs.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=Path("data/interim/dundee_sessions_clean.parquet"),
        help="Preferred cleaned Dundee input dataset.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/interim/dundee_sessions_clean.csv"),
        help="Fallback cleaned Dundee input dataset.",
    )
    parser.add_argument(
        "--station-master-out",
        type=Path,
        default=Path("data/processed/station_master.csv"),
    )
    parser.add_argument(
        "--chargepoint-master-out",
        type=Path,
        default=Path("data/processed/chargepoint_master.csv"),
    )
    parser.add_argument(
        "--station-locations-out",
        type=Path,
        default=Path("data/processed/station_locations.csv"),
    )
    parser.add_argument(
        "--station-catalog-geojson-out",
        type=Path,
        default=Path("data/processed/station_catalog.geojson"),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def configure_logging(level: str) -> None:
    """Configure module logging."""

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(levelname)s %(name)s: %(message)s",
    )


def mode_value(series: pd.Series) -> Any:
    """Return a deterministic mode value for text-like series."""

    values = series.dropna()
    if values.empty:
        return pd.NA
    modes = values.mode(dropna=True)
    if modes.empty:
        return sorted(str(value) for value in values)[0]
    return sorted(str(value) for value in modes)[0]


def sorted_unique_join(series: pd.Series) -> str:
    """Join unique non-null values in sorted order with semicolons."""

    unique_values = sorted({str(value) for value in series.dropna()})
    return ";".join(unique_values)


def assumed_power_kw(connector_type: Any) -> int:
    """Map a connector type to its V1 assumed power."""

    if pd.isna(connector_type):
        return 22
    return POWER_KW_BY_CONNECTOR.get(str(connector_type), 22)


def load_sessions(input_parquet: Path, input_csv: Path) -> pd.DataFrame:
    """Load the cleaned Dundee session dataset."""

    if input_parquet.exists():
        LOGGER.info("Loading cleaned Dundee sessions from %s", input_parquet)
        frame = pd.read_parquet(input_parquet)
    elif input_csv.exists():
        LOGGER.info("Loading cleaned Dundee sessions from %s", input_csv)
        frame = pd.read_csv(input_csv)
    else:
        raise FileNotFoundError(
            f"Neither cleaned input exists: {input_parquet} or {input_csv}"
        )

    required_columns = {
        "session_id",
        "station_id",
        "station_name",
        "postcode",
        "cp_id",
        "connector_type",
        "energy_kwh",
        "year",
    }
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required input columns: {missing_columns}")

    frame = frame.copy()
    text_columns = ["session_id", "station_id", "station_name", "postcode", "cp_id", "connector_type"]
    for column in text_columns:
        frame[column] = frame[column].astype("string").str.strip()
    frame["energy_kwh"] = pd.to_numeric(frame["energy_kwh"], errors="coerce")
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce").astype("Int64")
    return frame


def build_chargepoint_master(sessions: pd.DataFrame) -> pd.DataFrame:
    """Aggregate one row per unique charge point."""

    station_conflicts = (
        sessions.groupby("cp_id", dropna=False)["station_id"]
        .nunique(dropna=True)
        .reset_index(name="station_id_nunique")
    )
    conflicted_cp_ids = station_conflicts.loc[station_conflicts["station_id_nunique"] > 1, "cp_id"].dropna()
    if not conflicted_cp_ids.empty:
        LOGGER.warning(
            "Some cp_id values map to multiple Dundee stations; chargepoint_master uses the dominant station_id. Conflicts: %s",
            conflicted_cp_ids.astype(str).tolist(),
        )

    chargepoint_master = (
        sessions.groupby("cp_id", dropna=False)
        .agg(
            station_id=("station_id", mode_value),
            connector_type_mode=("connector_type", mode_value),
            first_seen_year=("year", "min"),
            last_seen_year=("year", "max"),
            sessions_total=("session_id", "count"),
        )
        .reset_index()
    )
    chargepoint_master["assumed_port_kw"] = chargepoint_master["connector_type_mode"].map(assumed_power_kw)
    chargepoint_master = chargepoint_master[
        [
            "cp_id",
            "station_id",
            "connector_type_mode",
            "assumed_port_kw",
            "first_seen_year",
            "last_seen_year",
            "sessions_total",
        ]
    ].sort_values(["station_id", "cp_id"], kind="stable")
    chargepoint_master["sessions_total"] = chargepoint_master["sessions_total"].astype(int)
    chargepoint_master["assumed_port_kw"] = chargepoint_master["assumed_port_kw"].astype(int)
    return chargepoint_master.reset_index(drop=True)


def location_seed_frame() -> pd.DataFrame:
    """Return the frozen Dundee location seed table."""

    seed = pd.DataFrame(LOCATION_SEED_ROWS)
    if seed["station_id"].duplicated().any():
        duplicates = seed.loc[seed["station_id"].duplicated(), "station_id"].tolist()
        raise ValueError(f"Duplicate station_ids in LOCATION_SEED_ROWS: {duplicates}")
    return seed


def build_station_locations(station_base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach frozen Dundee coordinates to the station list."""

    seed = location_seed_frame()
    merged = station_base.merge(seed, on="station_id", how="left")

    unresolved = merged["latitude"].isna() | merged["longitude"].isna()
    if unresolved.any():
        unresolved_station_ids = merged.loc[unresolved, "station_id"].tolist()
        LOGGER.warning("Stations without seeded coordinates: %s", unresolved_station_ids)
        merged.loc[unresolved, "location_source"] = "unresolved"
        merged.loc[unresolved, "location_confidence"] = "unresolved"
        merged.loc[unresolved, "needs_manual_review"] = True
        merged.loc[unresolved, "notes"] = "No deterministic Dundee location seed is available yet."

    merged["needs_manual_review"] = merged["needs_manual_review"].fillna(True).astype(bool)
    location_cols = [
        "station_id",
        "station_name",
        "postcode_mode",
        "latitude",
        "longitude",
        "location_source",
        "location_confidence",
        "needs_manual_review",
    ]
    station_locations = merged[location_cols].sort_values(["station_name", "station_id"], kind="stable")
    location_notes = merged[["station_id", "notes"]].copy()
    return station_locations.reset_index(drop=True), location_notes


def build_station_master(
    sessions: pd.DataFrame,
    station_locations: pd.DataFrame,
    location_notes: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate one row per unique station."""

    station_base = (
        sessions.groupby("station_id", dropna=False)
        .agg(
            station_name=("station_name", mode_value),
            postcode_mode=("postcode", mode_value),
            connector_mix_total=("connector_type", sorted_unique_join),
            first_seen_year=("year", "min"),
            last_seen_year=("year", "max"),
            sessions_total=("session_id", "count"),
            energy_total_kwh=("energy_kwh", lambda values: values.dropna().sum()),
        )
        .reset_index()
    )
    station_cp_rollup = (
        sessions.loc[sessions["cp_id"].notna(), ["station_id", "cp_id", "connector_type"]]
        .groupby(["station_id", "cp_id"], dropna=False)
        .agg(connector_type_mode=("connector_type", mode_value))
        .reset_index()
    )
    station_cp_rollup["assumed_port_kw"] = station_cp_rollup["connector_type_mode"].map(assumed_power_kw)
    cp_rollup = (
        station_cp_rollup.groupby("station_id", dropna=False)
        .agg(
            cp_count_total=("cp_id", "nunique"),
            station_max_power_kw_proxy=("assumed_port_kw", "sum"),
        )
        .reset_index()
    )
    station_master = (
        station_base.merge(cp_rollup, on="station_id", how="left")
        .merge(
            station_locations[
                ["station_id", "latitude", "longitude", "location_source"]
            ],
            on="station_id",
            how="left",
        )
        .merge(location_notes, on="station_id", how="left")
    )
    station_master["cp_count_total"] = station_master["cp_count_total"].fillna(0).astype(int)
    station_master["station_max_power_kw_proxy"] = (
        station_master["station_max_power_kw_proxy"].fillna(0).astype(int)
    )
    station_master["sessions_total"] = station_master["sessions_total"].astype(int)
    station_master["energy_total_kwh"] = station_master["energy_total_kwh"].fillna(0.0).round(3)
    station_master["notes"] = station_master["notes"].fillna("")

    ordered = [
        "station_id",
        "station_name",
        "postcode_mode",
        "cp_count_total",
        "connector_mix_total",
        "station_max_power_kw_proxy",
        "first_seen_year",
        "last_seen_year",
        "sessions_total",
        "energy_total_kwh",
        "latitude",
        "longitude",
        "location_source",
        "notes",
    ]
    return (
        station_master[ordered]
        .sort_values(["station_name", "station_id"], kind="stable")
        .reset_index(drop=True)
    )


def station_base_frame(sessions: pd.DataFrame) -> pd.DataFrame:
    """Build the minimal station list used by multiple outputs."""

    return (
        sessions.groupby("station_id", dropna=False)
        .agg(
            station_name=("station_name", mode_value),
            postcode_mode=("postcode", mode_value),
        )
        .reset_index()
    )


def build_geojson(station_master: pd.DataFrame) -> dict[str, Any]:
    """Convert the station catalog to a GeoJSON feature collection."""

    features: list[dict[str, Any]] = []
    for row in station_master.sort_values(["station_name", "station_id"], kind="stable").to_dict("records"):
        latitude = row["latitude"]
        longitude = row["longitude"]
        if pd.notna(latitude) and pd.notna(longitude):
            geometry: dict[str, Any] | None = {
                "type": "Point",
                "coordinates": [float(longitude), float(latitude)],
            }
        else:
            geometry = None
        properties = {
            "station_id": row["station_id"],
            "station_name": row["station_name"],
            "postcode_mode": row["postcode_mode"],
            "cp_count_total": int(row["cp_count_total"]),
            "connector_mix_total": row["connector_mix_total"],
            "station_max_power_kw_proxy": int(row["station_max_power_kw_proxy"]),
        }
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def ensure_parent(paths: list[Path]) -> None:
    """Create output directories when needed."""

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write a dataframe to CSV without the index."""

    frame.to_csv(path, index=False)


def write_geojson(payload: dict[str, Any], path: Path) -> None:
    """Write a GeoJSON document."""

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    """Run the Dundee station catalog build."""

    args = build_parser().parse_args()
    configure_logging(args.log_level)

    outputs = [
        args.station_master_out,
        args.chargepoint_master_out,
        args.station_locations_out,
        args.station_catalog_geojson_out,
    ]
    ensure_parent(outputs)

    sessions = load_sessions(args.input_parquet, args.input_csv)
    chargepoint_master = build_chargepoint_master(sessions)
    station_base = station_base_frame(sessions)
    station_locations, location_notes = build_station_locations(station_base)
    station_master = build_station_master(
        sessions=sessions,
        station_locations=station_locations,
        location_notes=location_notes,
    )
    geojson = build_geojson(station_master)

    write_csv(station_master, args.station_master_out)
    write_csv(chargepoint_master, args.chargepoint_master_out)
    write_csv(station_locations, args.station_locations_out)
    write_geojson(geojson, args.station_catalog_geojson_out)

    LOGGER.info("Wrote %s", args.station_master_out)
    LOGGER.info("Wrote %s", args.chargepoint_master_out)
    LOGGER.info("Wrote %s", args.station_locations_out)
    LOGGER.info("Wrote %s", args.station_catalog_geojson_out)
    LOGGER.info(
        "Built Dundee catalog with %s stations and %s charge points.",
        len(station_master),
        len(chargepoint_master),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
