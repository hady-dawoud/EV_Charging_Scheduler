"""Build simulator-ready Dundee spatial structure from verified station locations.

This script is intentionally additive and Dundee-only. It does not modify the
canonical cleaned session artifacts or any application code. The outputs are
synthetic planning layers for simulator V1:

- a manual coordinate override workflow
- a verified station-location layer with final coordinates
- four simulator zones
- eight synthetic transformers
- station and transformer capacity assumptions
- review notes and presentation maps

Important: the zone and transformer topology created here is not verified SSEN
network truth. It is a documented simulator scaffold derived from the Dundee
station inventory and reviewed location seeds.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any

import folium
import matplotlib.pyplot as plt
import pandas as pd

LOGGER = logging.getLogger("dundee_spatial_topology")

ZONE_COLORS = {
    "zone_central_waterfront": "#1d4ed8",
    "zone_west_lochee": "#15803d",
    "zone_north_inner": "#c2410c",
    "zone_east_corridor": "#7c3aed",
}

FOLLOWUP_REASONS = {
    "alexander_street_dundee": "Current point is a postcode centroid rather than a charger-level placement.",
    "caird_avenue": "Current point is a low-confidence road-only match with no postcode in the source data.",
    "camperdown_country_park": "Current point is a park feature centroid and may not align with the charger bays.",
    "clepington_road_4th_hub": "Current point is a postcode centroid for a major hub and should be pinned more precisely.",
    "dundee_taybridge_rail_station_south_union_street_dundee": "Current point shares the railway-station location and should be confirmed at site level.",
    "greenmarket_150kw_bus_charger": "Current point is a postcode centroid for a high-power bus charger and should be manually pinned.",
    "housing_office_east_midmill_road_dundee": "Current point is a postcode centroid and should be confirmed against the exact site frontage.",
}

ZONE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "zone_central_waterfront": {
        "zone_name": "Central Waterfront & City Core",
        "zone_description": "City-centre and waterfront stations around the railway, Greenmarket, Gellatly Street, Olympia, Dock Street, and Princes Street.",
        "design_basis": "Grouped as the dense central charging core around the waterfront corridor and adjacent city-centre streets.",
        "station_ids": [
            "dock_street_dundee",
            "dundee_house_depot_north_lindsay_street_dundee",
            "dundee_railway_station",
            "dundee_taybridge_rail_station_south_union_street_dundee",
            "gellatly_street_car_park_dundee",
            "greenmarket_150kw_bus_charger",
            "greenmarket_multi_storey_car_park_dundee",
            "nethergate_dundee",
            "olympia_hub",
            "olympia_multi_storey_car_park_dundee",
            "princes_street_charging_hub_dundee",
            "south_tay_street_car_club_public",
            "trades_lane_dundee",
        ],
    },
    "zone_west_lochee": {
        "zone_name": "West Lochee & Camperdown",
        "zone_description": "Stations serving Lochee, Menzieshill, Camperdown, and the western side of Dundee.",
        "design_basis": "Grouped as the western corridor around the Lochee hub, western residential sites, and Camperdown/Ice Arena activity.",
        "station_ids": [
            "camperdown_country_park",
            "craigowen_road",
            "deveron_terrace",
            "dundee_ice_arena_dundee",
            "lochee_charging_hub_aimer_square_dundee",
            "menzieshill_community_centre",
            "orleans_place_dundee",
        ],
    },
    "zone_north_inner": {
        "zone_name": "North Inner Residential",
        "zone_description": "North-central and north-eastern inner-city stations around Coldside, Clepington, Midmill, Mill O' Mains, and Alexander Street.",
        "design_basis": "Grouped as the inner northern residential belt linking Coldside/Clepington with Midmill and Mid Craigie.",
        "station_ids": [
            "alexander_street_dundee",
            "caird_avenue",
            "clepington_road_4th_hub",
            "coldside_nursery",
            "derby_street",
            "housing_office_east_midmill_road_dundee",
            "mill_o_mains_primary_school",
            "rpc_dundee",
        ],
    },
    "zone_east_corridor": {
        "zone_name": "East Corridor & Broughty",
        "zone_description": "Eastern Dundee stations from Queen Street and Michelin through Douglas, Whitfield, and Broughty Ferry.",
        "design_basis": "Grouped as the eastern corridor spanning the major Queen Street hub and the outer eastern neighbourhood sites.",
        "station_ids": [
            "balmerino_road",
            "dawson_park_broughty_ferry",
            "douglas_community_library",
            "eastern_primary_school",
            "michelin_scotland_innovation_park",
            "queen_street_charging_hub_dundee",
            "whitfield_centre_lothian_crescent_dundee",
        ],
    },
}

TRANSFORMER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "tx_central_market": {
        "transformer_name": "Central Market Feeder",
        "map_label": "T1",
        "zone_id": "zone_central_waterfront",
        "station_ids": [
            "dundee_railway_station",
            "dundee_taybridge_rail_station_south_union_street_dundee",
            "greenmarket_150kw_bus_charger",
            "greenmarket_multi_storey_car_park_dundee",
            "nethergate_dundee",
            "south_tay_street_car_club_public",
        ],
    },
    "tx_central_waterfront": {
        "transformer_name": "Central Waterfront Feeder",
        "map_label": "T2",
        "zone_id": "zone_central_waterfront",
        "station_ids": [
            "dock_street_dundee",
            "dundee_house_depot_north_lindsay_street_dundee",
            "gellatly_street_car_park_dundee",
            "olympia_hub",
            "olympia_multi_storey_car_park_dundee",
            "princes_street_charging_hub_dundee",
            "trades_lane_dundee",
        ],
    },
    "tx_west_lochee": {
        "transformer_name": "West Lochee Feeder",
        "map_label": "T3",
        "zone_id": "zone_west_lochee",
        "station_ids": [
            "craigowen_road",
            "deveron_terrace",
            "lochee_charging_hub_aimer_square_dundee",
            "menzieshill_community_centre",
            "orleans_place_dundee",
        ],
    },
    "tx_west_camperdown": {
        "transformer_name": "West Camperdown Feeder",
        "map_label": "T4",
        "zone_id": "zone_west_lochee",
        "station_ids": [
            "camperdown_country_park",
            "dundee_ice_arena_dundee",
        ],
    },
    "tx_north_clepington": {
        "transformer_name": "North Clepington Feeder",
        "map_label": "T5",
        "zone_id": "zone_north_inner",
        "station_ids": [
            "alexander_street_dundee",
            "caird_avenue",
            "clepington_road_4th_hub",
            "coldside_nursery",
        ],
    },
    "tx_north_midcraigie": {
        "transformer_name": "North Mid Craigie Feeder",
        "map_label": "T6",
        "zone_id": "zone_north_inner",
        "station_ids": [
            "derby_street",
            "housing_office_east_midmill_road_dundee",
            "mill_o_mains_primary_school",
            "rpc_dundee",
        ],
    },
    "tx_east_queen_street": {
        "transformer_name": "East Queen Street Feeder",
        "map_label": "T7",
        "zone_id": "zone_east_corridor",
        "station_ids": [
            "eastern_primary_school",
            "michelin_scotland_innovation_park",
            "queen_street_charging_hub_dundee",
        ],
    },
    "tx_east_broughty": {
        "transformer_name": "East Broughty Feeder",
        "map_label": "T8",
        "zone_id": "zone_east_corridor",
        "station_ids": [
            "balmerino_road",
            "dawson_park_broughty_ferry",
            "douglas_community_library",
            "whitfield_centre_lothian_crescent_dundee",
        ],
    },
}

TRANSFORMER_DIVERSITY_FACTOR = 0.85


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line interface."""

    parser = argparse.ArgumentParser(description="Build Dundee simulator spatial topology and review artifacts.")
    parser.add_argument("--station-master", type=Path, default=Path("data/processed/station_master.csv"))
    parser.add_argument("--station-locations", type=Path, default=Path("data/processed/station_locations.csv"))
    parser.add_argument("--station-catalog-geojson", type=Path, default=Path("data/processed/station_catalog.geojson"))
    parser.add_argument(
        "--review-map-paths",
        type=Path,
        nargs="*",
        default=[
            Path("outputs/maps/dundee_station_map_interactive.html"),
            Path("outputs/maps/dundee_station_map_interactive_by_cp_count.html"),
            Path("outputs/maps/dundee_station_map_interactive_by_sessions.html"),
        ],
    )
    parser.add_argument("--overrides-csv", type=Path, default=Path("data/processed/station_location_overrides.csv"))
    parser.add_argument(
        "--verified-locations-csv",
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
    parser.add_argument(
        "--zone-map-html",
        type=Path,
        default=Path("outputs/maps/dundee_zone_transformer_map.html"),
    )
    parser.add_argument(
        "--zone-map-png",
        type=Path,
        default=Path("outputs/figures/dundee_zone_transformer_map.png"),
    )
    parser.add_argument(
        "--location-review-summary-md",
        type=Path,
        default=Path("outputs/qc/station_location_review_summary.md"),
    )
    parser.add_argument(
        "--zone-design-notes-md",
        type=Path,
        default=Path("outputs/qc/dundee_zone_design_notes.md"),
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
    """Create parent directories for the given output paths."""

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def apply_plot_style() -> None:
    """Set a consistent plot style for Dundee spatial outputs."""

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#f8fafc",
            "axes.edgecolor": "#0f172a",
            "axes.labelcolor": "#0f172a",
            "text.color": "#0f172a",
            "xtick.color": "#0f172a",
            "ytick.color": "#0f172a",
            "grid.color": "#dbeafe",
            "font.size": 10,
            "axes.titleweight": "bold",
        }
    )


def round_up(value: float, increment: int) -> int:
    """Round a numeric value up to the nearest increment."""

    if value <= 0:
        return increment
    return int(math.ceil(value / increment) * increment)


def parse_bool(value: Any) -> bool:
    """Parse mixed boolean-like CSV values."""

    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def load_station_inputs(station_master_path: Path, station_locations_path: Path, station_catalog_geojson: Path) -> pd.DataFrame:
    """Load the Dundee station inventory and preserve the original location seed fields."""

    for path in [station_master_path, station_locations_path, station_catalog_geojson]:
        if not path.exists():
            raise FileNotFoundError(f"Missing required Dundee input: {path}")

    with station_catalog_geojson.open("r", encoding="utf-8") as handle:
        geojson = json.load(handle)
    geojson_station_ids = {
        feature.get("properties", {}).get("station_id")
        for feature in geojson.get("features", [])
        if feature.get("properties", {}).get("station_id")
    }

    station_master = pd.read_csv(station_master_path)
    station_locations = pd.read_csv(station_locations_path)
    station_locations["needs_manual_review"] = station_locations["needs_manual_review"].map(parse_bool)

    merged = station_master.merge(
        station_locations,
        on=["station_id", "station_name", "postcode_mode"],
        how="inner",
        suffixes=("", "_location"),
    )
    merged = merged.rename(
        columns={
            "latitude": "original_latitude",
            "longitude": "original_longitude",
            "location_source": "original_location_source",
            "location_confidence": "original_location_confidence",
            "needs_manual_review": "original_needs_manual_review",
            "notes": "original_location_notes",
        }
    )

    master_station_ids = set(merged["station_id"])
    if master_station_ids != geojson_station_ids:
        missing_from_geojson = sorted(master_station_ids - geojson_station_ids)
        missing_from_master = sorted(geojson_station_ids - master_station_ids)
        raise ValueError(
            "Station catalog mismatch between CSV and GeoJSON. "
            f"Missing in GeoJSON: {missing_from_geojson}. Missing in station master: {missing_from_master}."
        )

    merged["original_latitude"] = pd.to_numeric(merged["original_latitude"], errors="coerce")
    merged["original_longitude"] = pd.to_numeric(merged["original_longitude"], errors="coerce")
    merged["cp_count_total"] = pd.to_numeric(merged["cp_count_total"], errors="coerce").astype("int64")
    merged["station_max_power_kw_proxy"] = pd.to_numeric(merged["station_max_power_kw_proxy"], errors="coerce")
    merged["sessions_total"] = pd.to_numeric(merged["sessions_total"], errors="coerce").astype("int64")
    return merged.sort_values(["station_name", "station_id"], kind="stable").reset_index(drop=True)


def refresh_override_workflow(stations: pd.DataFrame, overrides_path: Path) -> pd.DataFrame:
    """Create or refresh the override workflow while preserving existing manual edits."""

    manual_columns = [
        "override_latitude",
        "override_longitude",
        "override_source",
        "override_reason",
        "override_location_confidence",
        "reviewer",
        "reviewed_at",
    ]
    base = stations[
        [
            "station_id",
            "station_name",
            "postcode_mode",
            "original_latitude",
            "original_longitude",
            "original_location_source",
            "original_location_confidence",
            "original_needs_manual_review",
        ]
    ].copy()
    base["review_recommendation"] = base["station_id"].map(
        lambda station_id: "needs_followup" if station_id in FOLLOWUP_REASONS else "accepted_current"
    )
    base["review_note_seed"] = base["station_id"].map(
        lambda station_id: FOLLOWUP_REASONS.get(
            station_id,
            "Current coordinates are acceptable for simulator V1 and can remain unless a better site-level point is available.",
        )
    )

    if overrides_path.exists():
        existing = pd.read_csv(overrides_path, keep_default_na=False)
        keep_columns = ["station_id"] + [column for column in manual_columns if column in existing.columns]
        existing = existing[keep_columns].copy()
    else:
        existing = pd.DataFrame(columns=["station_id", *manual_columns])

    merged = base.merge(existing, on="station_id", how="left")
    for column in manual_columns:
        if column not in merged.columns:
            merged[column] = ""
        merged[column] = merged[column].fillna("")

    merged = merged.sort_values(["review_recommendation", "station_name"], ascending=[False, True], kind="stable")
    merged.to_csv(overrides_path, index=False)
    return merged


def build_verified_locations(stations: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Produce the verified Dundee location layer with final coordinates and statuses."""

    verified = stations.merge(
        overrides[
            [
                "station_id",
                "override_latitude",
                "override_longitude",
                "override_source",
                "override_reason",
                "override_location_confidence",
                "reviewer",
                "reviewed_at",
            ]
        ],
        on="station_id",
        how="left",
    )
    verified["override_latitude"] = pd.to_numeric(verified["override_latitude"], errors="coerce")
    verified["override_longitude"] = pd.to_numeric(verified["override_longitude"], errors="coerce")
    for column in ["override_source", "override_reason", "override_location_confidence", "reviewer", "reviewed_at"]:
        verified[column] = verified[column].fillna("")

    has_full_override = verified["override_latitude"].notna() & verified["override_longitude"].notna()
    has_partial_override = verified["override_latitude"].notna() ^ verified["override_longitude"].notna()

    verified["final_latitude"] = verified["override_latitude"].where(has_full_override, verified["original_latitude"])
    verified["final_longitude"] = verified["override_longitude"].where(has_full_override, verified["original_longitude"])
    verified["final_location_source"] = verified["override_source"].where(
        has_full_override,
        verified["original_location_source"],
    )
    verified["final_location_source"] = verified["final_location_source"].replace("", "manual_override")

    verified["verification_status"] = "accepted_current"
    verified.loc[verified["station_id"].isin(FOLLOWUP_REASONS), "verification_status"] = "needs_followup"
    verified.loc[has_partial_override, "verification_status"] = "needs_followup"
    verified.loc[has_full_override, "verification_status"] = "manually_overridden"

    verified["location_confidence_final"] = verified["original_location_confidence"].fillna("unknown")
    verified.loc[verified["verification_status"].eq("accepted_current"), "location_confidence_final"] = verified.loc[
        verified["verification_status"].eq("accepted_current"),
        "original_location_confidence",
    ].fillna("medium")
    verified.loc[verified["verification_status"].eq("needs_followup"), "location_confidence_final"] = verified.loc[
        verified["verification_status"].eq("needs_followup"),
        "original_location_confidence",
    ].fillna("medium")
    verified.loc[verified["verification_status"].eq("manually_overridden"), "location_confidence_final"] = verified.loc[
        verified["verification_status"].eq("manually_overridden"),
        "override_location_confidence",
    ].replace("", "high")

    verified["verification_notes"] = verified["station_id"].map(
        lambda station_id: FOLLOWUP_REASONS.get(
            station_id,
            "Accepted current coordinates for simulator V1 after location review.",
        )
    )
    verified.loc[has_partial_override, "verification_notes"] = (
        "Override was partially filled; original coordinates were kept until both override fields are supplied."
    )
    verified.loc[has_full_override, "verification_notes"] = verified.loc[has_full_override, "override_reason"].replace(
        "",
        "Manual coordinates supplied in station_location_overrides.csv.",
    )
    verified["original_needs_manual_review"] = verified["original_needs_manual_review"].map(parse_bool)
    verified["needs_followup_flag"] = verified["verification_status"].eq("needs_followup")

    columns = [
        "station_id",
        "station_name",
        "postcode_mode",
        "original_latitude",
        "original_longitude",
        "original_location_source",
        "original_location_confidence",
        "original_needs_manual_review",
        "override_latitude",
        "override_longitude",
        "override_source",
        "override_reason",
        "final_latitude",
        "final_longitude",
        "final_location_source",
        "verification_status",
        "location_confidence_final",
        "needs_followup_flag",
        "verification_notes",
        "reviewer",
        "reviewed_at",
    ]
    return verified[columns].sort_values(["station_name", "station_id"], kind="stable").reset_index(drop=True)


def build_zone_map(stations: pd.DataFrame) -> pd.DataFrame:
    """Assign every Dundee station to exactly one simulator zone."""

    rows: list[dict[str, Any]] = []
    for zone_id, metadata in ZONE_DEFINITIONS.items():
        for station_id in metadata["station_ids"]:
            rows.append(
                {
                    "station_id": station_id,
                    "zone_id": zone_id,
                    "zone_name": metadata["zone_name"],
                    "zone_description": metadata["zone_description"],
                    "zone_design_basis": metadata["design_basis"],
                }
            )
    zone_map = pd.DataFrame(rows)
    validate_station_cover("zone", stations["station_id"], zone_map["station_id"])
    return zone_map.sort_values(["zone_id", "station_id"], kind="stable").reset_index(drop=True)


def build_transformer_map(stations: pd.DataFrame, zone_map: pd.DataFrame) -> pd.DataFrame:
    """Assign every Dundee station to exactly one synthetic transformer."""

    rows: list[dict[str, Any]] = []
    for transformer_id, metadata in TRANSFORMER_DEFINITIONS.items():
        for station_id in metadata["station_ids"]:
            rows.append(
                {
                    "station_id": station_id,
                    "transformer_id": transformer_id,
                    "transformer_name": metadata["transformer_name"],
                    "transformer_map_label": metadata["map_label"],
                    "zone_id": metadata["zone_id"],
                    "topology_source": "synthetic_planning_assumption",
                    "notes": "Synthetic simulator feeder assignment; not verified utility topology.",
                }
            )
    transformer_map = pd.DataFrame(rows)
    validate_station_cover("transformer", stations["station_id"], transformer_map["station_id"])

    merged = transformer_map.merge(zone_map[["station_id", "zone_id"]], on="station_id", how="left", suffixes=("", "_zone"))
    mismatch = merged[merged["zone_id"] != merged["zone_id_zone"]]
    if not mismatch.empty:
        raise ValueError(
            "Transformer zone assignment mismatch for stations: "
            f"{sorted(mismatch['station_id'].unique().tolist())}"
        )
    return transformer_map.sort_values(["transformer_id", "station_id"], kind="stable").reset_index(drop=True)


def validate_station_cover(mapping_name: str, station_ids: pd.Series, mapped_station_ids: pd.Series) -> None:
    """Ensure each station appears exactly once in a mapping layer."""

    duplicates = mapped_station_ids[mapped_station_ids.duplicated()].tolist()
    if duplicates:
        raise ValueError(f"Duplicate {mapping_name} assignments found for stations: {duplicates}")

    station_set = set(station_ids)
    mapped_set = set(mapped_station_ids)
    if station_set != mapped_set:
        missing = sorted(station_set - mapped_set)
        extra = sorted(mapped_set - station_set)
        raise ValueError(
            f"{mapping_name.title()} mapping coverage mismatch. Missing: {missing}. Extra: {extra}."
        )


def connector_diversity_factor(connector_mix_total: str) -> tuple[float, str]:
    """Return the station-level diversity factor based on connector mix."""

    connector_types = {item.strip() for item in str(connector_mix_total).split(";") if item.strip()}
    if "ultra_rapid" in connector_types:
        return 0.85, "Ultra-rapid mix uses 85% of proxy connected power before station rounding."
    if "rapid" in connector_types:
        return 0.90, "Rapid mix uses 90% of proxy connected power before station rounding."
    return 1.00, "AC-only default uses 22 kW per port as the station feeder proxy."


def build_station_capacity_assumptions(
    stations: pd.DataFrame,
    verified_locations: pd.DataFrame,
    zone_map: pd.DataFrame,
    transformer_map: pd.DataFrame,
) -> pd.DataFrame:
    """Create per-station synthetic capacity assumptions for simulator V1."""

    capacity = stations.merge(zone_map, on="station_id", how="left").merge(
        transformer_map[["station_id", "transformer_id", "transformer_name", "transformer_map_label"]],
        on="station_id",
        how="left",
    )
    capacity = capacity.merge(
        verified_locations[["station_id", "verification_status", "location_confidence_final"]],
        on="station_id",
        how="left",
    )

    factors = capacity["connector_mix_total"].map(connector_diversity_factor)
    capacity["station_diversity_factor"] = factors.map(lambda item: item[0])
    capacity["capacity_method_notes"] = factors.map(lambda item: item[1])
    capacity["baseline_port_capacity_kw"] = capacity["cp_count_total"] * 22
    diversified_proxy = capacity["station_max_power_kw_proxy"] * capacity["station_diversity_factor"]
    capacity["station_capacity_kw_assumed"] = (
        pd.concat([capacity["baseline_port_capacity_kw"], diversified_proxy], axis=1)
        .max(axis=1)
        .map(lambda value: round_up(float(value), 10))
    )
    capacity["capacity_method"] = "max(cp_count_total*22, station_max_power_kw_proxy*station_diversity_factor)"
    capacity["topology_source"] = "synthetic_planning_assumption"
    capacity["notes"] = (
        "Synthetic station capacity used for simulator V1; not a verified DNO connection limit."
    )

    columns = [
        "station_id",
        "station_name",
        "zone_id",
        "zone_name",
        "transformer_id",
        "transformer_name",
        "transformer_map_label",
        "cp_count_total",
        "connector_mix_total",
        "station_max_power_kw_proxy",
        "baseline_port_capacity_kw",
        "station_diversity_factor",
        "station_capacity_kw_assumed",
        "capacity_method",
        "capacity_method_notes",
        "verification_status",
        "location_confidence_final",
        "topology_source",
        "notes",
    ]
    return capacity[columns].sort_values(["zone_id", "transformer_id", "station_name"], kind="stable").reset_index(drop=True)


def build_zones(
    verified_locations: pd.DataFrame,
    station_capacity_assumptions: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate zone metadata and centroids from verified station locations."""

    merged = station_capacity_assumptions.merge(
        verified_locations[["station_id", "final_latitude", "final_longitude"]],
        on="station_id",
        how="left",
    )
    rows: list[dict[str, Any]] = []
    for zone_id, metadata in ZONE_DEFINITIONS.items():
        subset = merged[merged["zone_id"] == zone_id].copy()
        rows.append(
            {
                "zone_id": zone_id,
                "zone_name": metadata["zone_name"],
                "zone_description": metadata["zone_description"],
                "design_basis": metadata["design_basis"],
                "station_count": int(len(subset)),
                "cp_count_total_proxy": int(subset["cp_count_total"].sum()),
                "station_capacity_kw_total": int(subset["station_capacity_kw_assumed"].sum()),
                "centroid_latitude": round(float(subset["final_latitude"].mean()), 6),
                "centroid_longitude": round(float(subset["final_longitude"].mean()), 6),
                "topology_source": "synthetic_planning_assumption",
                "notes": "Simulator zone grouping for V1; not a formal network boundary.",
            }
        )
    return pd.DataFrame(rows).sort_values("zone_id", kind="stable").reset_index(drop=True)


def build_transformers(
    verified_locations: pd.DataFrame,
    station_capacity_assumptions: pd.DataFrame,
    transformer_map: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate synthetic transformer metadata from attached stations."""

    merged = station_capacity_assumptions.merge(
        verified_locations[["station_id", "final_latitude", "final_longitude"]],
        on="station_id",
        how="left",
    ).merge(
        transformer_map[["station_id", "transformer_id", "transformer_name", "transformer_map_label", "zone_id"]],
        on=["station_id", "transformer_id"],
        how="left",
        suffixes=("", "_map"),
    )

    rows: list[dict[str, Any]] = []
    for transformer_id, metadata in TRANSFORMER_DEFINITIONS.items():
        subset = merged[merged["transformer_id"] == transformer_id].copy()
        attached_station_capacity_kw_sum = float(subset["station_capacity_kw_assumed"].sum())
        rows.append(
            {
                "transformer_id": transformer_id,
                "transformer_name": metadata["transformer_name"],
                "transformer_map_label": metadata["map_label"],
                "zone_id": metadata["zone_id"],
                "station_count": int(len(subset)),
                "cp_count_total_proxy": int(subset["cp_count_total"].sum()),
                "attached_station_capacity_kw_sum": int(attached_station_capacity_kw_sum),
                "transformer_diversity_factor": TRANSFORMER_DIVERSITY_FACTOR,
                "transformer_capacity_kw_assumed": round_up(
                    attached_station_capacity_kw_sum * TRANSFORMER_DIVERSITY_FACTOR,
                    50,
                ),
                "latitude": round(float(subset["final_latitude"].mean()), 6),
                "longitude": round(float(subset["final_longitude"].mean()), 6),
                "topology_source": "synthetic_planning_assumption",
                "notes": (
                    "Synthetic simulator transformer sized from attached station capacities using "
                    "a documented diversity factor, not real utility data."
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("transformer_id", kind="stable").reset_index(drop=True)


def create_station_popup(row: pd.Series) -> folium.Popup:
    """Create the required popup for station markers."""

    rows = [
        ("Station Name", row["station_name"]),
        ("Station ID", row["station_id"]),
        ("Zone ID", row["zone_id"]),
        ("Transformer ID", row["transformer_id"]),
        ("Postcode", row["postcode_mode"]),
        ("Charge Points", int(row["cp_count_total"])),
        ("Connector Mix", row["connector_mix_total"]),
        ("Station Capacity Assumed (kW)", int(row["station_capacity_kw_assumed"])),
        ("Station Max Power Proxy (kW)", int(row["station_max_power_kw_proxy"])),
        ("Sessions Total", int(row["sessions_total"])),
    ]
    html_rows = "".join(
        f"<tr><th style='text-align:left;padding-right:8px;'>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    return folium.Popup(f"<table>{html_rows}</table>", max_width=380)


def create_transformer_popup(row: pd.Series) -> folium.Popup:
    """Create the popup for synthetic transformer markers."""

    rows = [
        ("Transformer", row["transformer_name"]),
        ("Transformer ID", row["transformer_id"]),
        ("Map Label", row["transformer_map_label"]),
        ("Zone ID", row["zone_id"]),
        ("Stations Attached", int(row["station_count"])),
        ("CP Count Proxy", int(row["cp_count_total_proxy"])),
        ("Attached Station Capacity Sum (kW)", int(row["attached_station_capacity_kw_sum"])),
        ("Transformer Capacity Assumed (kW)", int(row["transformer_capacity_kw_assumed"])),
        ("Topology Source", row["topology_source"]),
    ]
    html_rows = "".join(
        f"<tr><th style='text-align:left;padding-right:8px;'>{label}</th><td>{value}</td></tr>"
        for label, value in rows
    )
    return folium.Popup(f"<table>{html_rows}</table>", max_width=420)


def add_zone_legend(fmap: folium.Map) -> None:
    """Add a fixed legend to the Folium map."""

    legend_rows = [
        "<div style=\"position: fixed; bottom: 30px; left: 30px; z-index: 9999; "
        "background: white; border: 2px solid #0f172a; border-radius: 8px; padding: 12px; "
        "font-size: 12px; line-height: 1.4; box-shadow: 0 4px 14px rgba(15,23,42,0.15);\">",
        "<div style=\"font-weight: 700; margin-bottom: 8px;\">Dundee Simulator V1</div>",
    ]
    for zone_id, metadata in ZONE_DEFINITIONS.items():
        color = ZONE_COLORS[zone_id]
        legend_rows.append(
            f"<div><span style=\"display:inline-block;width:12px;height:12px;background:{color};"
            f"border:1px solid #0f172a;margin-right:6px;\"></span>{metadata['zone_name']}</div>"
        )
    legend_rows.append(
        "<div style=\"margin-top:8px;\"><span style=\"display:inline-block;width:0;height:0;"
        "border-left:7px solid transparent;border-right:7px solid transparent;"
        "border-bottom:12px solid #111827;margin-right:6px;\"></span>Synthetic transformer</div>"
    )
    legend_rows.append("</div>")
    fmap.get_root().html.add_child(folium.Element("".join(legend_rows)))


def build_zone_transformer_map_html(
    stations_for_map: pd.DataFrame,
    transformers: pd.DataFrame,
    output_path: Path,
) -> None:
    """Build the interactive Dundee zone and transformer map."""

    center = [stations_for_map["final_latitude"].mean(), stations_for_map["final_longitude"].mean()]
    fmap = folium.Map(location=center, zoom_start=12, control_scale=True, tiles=None)
    folium.TileLayer("CartoDB positron", name="CartoDB Positron", control=False).add_to(fmap)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(fmap)

    station_group = folium.FeatureGroup(name="Stations", show=True)
    transformer_group = folium.FeatureGroup(name="Synthetic transformers", show=True)

    for _, row in stations_for_map.iterrows():
        zone_color = ZONE_COLORS[row["zone_id"]]
        folium.CircleMarker(
            location=[row["final_latitude"], row["final_longitude"]],
            radius=6 + min(int(row["cp_count_total"]), 10) * 0.5,
            color="#0f172a",
            weight=1.2,
            fill=True,
            fill_color=zone_color,
            fill_opacity=0.92,
            popup=create_station_popup(row),
            tooltip=f"{row['station_name']} | {row['zone_name']} | {row['transformer_map_label']}",
        ).add_to(station_group)

    for _, row in transformers.iterrows():
        folium.RegularPolygonMarker(
            location=[row["latitude"], row["longitude"]],
            number_of_sides=3,
            radius=12,
            rotation=0,
            color="#111827",
            weight=2,
            fill=True,
            fill_color="#f59e0b",
            fill_opacity=0.95,
            popup=create_transformer_popup(row),
            tooltip=f"{row['transformer_map_label']} | {row['transformer_name']}",
        ).add_to(transformer_group)
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            icon=folium.DivIcon(
                html=(
                    "<div style='font-size:11px;font-weight:700;color:#111827;"
                    "background:rgba(255,255,255,0.85);padding:1px 4px;border-radius:4px;'>"
                    f"{row['transformer_map_label']}</div>"
                )
            ),
        ).add_to(transformer_group)

    station_group.add_to(fmap)
    transformer_group.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)
    add_zone_legend(fmap)
    fmap.save(str(output_path))


def build_zone_transformer_map_png(
    stations_for_map: pd.DataFrame,
    transformers: pd.DataFrame,
    output_path: Path,
) -> None:
    """Build a static PNG map for reports and slides."""

    apply_plot_style()
    fig, ax = plt.subplots(figsize=(11, 8))

    for zone_id, metadata in ZONE_DEFINITIONS.items():
        subset = stations_for_map[stations_for_map["zone_id"] == zone_id].copy()
        ax.scatter(
            subset["final_longitude"],
            subset["final_latitude"],
            s=65 + subset["cp_count_total"] * 7,
            c=ZONE_COLORS[zone_id],
            edgecolors="#0f172a",
            linewidths=0.8,
            alpha=0.92,
            label=metadata["zone_name"],
        )

    followup = stations_for_map[stations_for_map["verification_status"] == "needs_followup"].copy()
    if not followup.empty:
        ax.scatter(
            followup["final_longitude"],
            followup["final_latitude"],
            s=160,
            facecolors="none",
            edgecolors="#ef4444",
            linewidths=1.5,
            label="Needs follow-up",
        )

    ax.scatter(
        transformers["longitude"],
        transformers["latitude"],
        s=220,
        c="#111827",
        marker="^",
        edgecolors="#f8fafc",
        linewidths=0.9,
        label="Synthetic transformer",
        zorder=5,
    )

    for _, row in transformers.iterrows():
        ax.annotate(
            row["transformer_map_label"],
            (row["longitude"], row["latitude"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
            fontweight="bold",
            color="#111827",
        )

    ax.set_title("Dundee Simulator Zones and Synthetic Transformers")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.text(
        0.01,
        0.01,
        "Synthetic simulator topology for V1 only; not verified SSEN network truth.",
        transform=ax.transAxes,
        fontsize=9,
        color="#475569",
    )
    ax.legend(loc="upper left", frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_location_review_summary(
    verified_locations: pd.DataFrame,
    overrides_path: Path,
    review_map_paths: list[Path],
    output_path: Path,
) -> None:
    """Write the Dundee station location review summary."""

    status_counts = verified_locations["verification_status"].value_counts().to_dict()
    followup = verified_locations[verified_locations["verification_status"] == "needs_followup"].copy()

    lines = [
        "# Dundee Station Location Review Summary",
        "",
        "This layer preserves the original station location seeds and adds a reproducible manual-override workflow.",
        "",
        "## Counts",
        f"- Total stations: {len(verified_locations)}",
        f"- `accepted_current`: {status_counts.get('accepted_current', 0)}",
        f"- `manually_overridden`: {status_counts.get('manually_overridden', 0)}",
        f"- `needs_followup`: {status_counts.get('needs_followup', 0)}",
        f"- Override workflow file: `{overrides_path.as_posix()}`",
        "",
        "## Review Basis",
        "- Original location source and confidence from `station_locations.csv` were preserved.",
        "- Existing Dundee interactive maps were used as the visual-review artifacts that motivate this workflow.",
        "- Any station still marked `needs_followup` keeps its current coordinates as a temporary simulator placeholder until a manual override is supplied.",
        "",
        "## Review Artifacts",
    ]
    lines.extend(f"- `{path.as_posix()}`" for path in review_map_paths)
    lines.extend(
        [
            "",
            "## Stations Still Needing Follow-up",
            "",
            "| station_id | station_name | current_source | confidence | reason |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in followup.sort_values("station_name", kind="stable").iterrows():
        lines.append(
            f"| {row['station_id']} | {row['station_name']} | {row['original_location_source']} | "
            f"{row['original_location_confidence']} | {row['verification_notes']} |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_zone_design_notes(
    zones: pd.DataFrame,
    transformers: pd.DataFrame,
    verified_locations: pd.DataFrame,
    output_path: Path,
) -> None:
    """Write Dundee zone and transformer design notes for simulator V1."""

    followup = verified_locations[verified_locations["verification_status"] == "needs_followup"].copy()
    lines = [
        "# Dundee Zone Design Notes",
        "",
        "This topology is a simulator scaffold for V1. It is not verified SSEN network truth and should not be treated as a real feeder map.",
        "",
        "## Zone Definitions",
    ]
    for _, row in zones.sort_values("zone_id", kind="stable").iterrows():
        lines.extend(
            [
                f"### {row['zone_name']} (`{row['zone_id']}`)",
                f"- Stations: {int(row['station_count'])}",
                f"- CP count proxy: {int(row['cp_count_total_proxy'])}",
                f"- Assumed station capacity total: {int(row['station_capacity_kw_total'])} kW",
                f"- Why this zone: {row['design_basis']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Transformer Design",
            f"- Transformer count: {len(transformers)}",
            "- Each station is assigned to exactly one synthetic transformer so the simulator has a single upstream attachment point per station.",
            "- The transformer count was chosen to keep the topology simple enough for V1 while still separating the biggest hubs into distinct local groups.",
            "",
            "## Capacity Assumptions",
            "- Station capacity uses `cp_count_total` as the default port-count proxy at 22 kW per port.",
            "- Rapid and ultra-rapid sites also use the station connected-power proxy, diversified before rounding to avoid assuming full simultaneous nameplate draw.",
            "- Formula: `station_capacity_kw_assumed = round_up(max(cp_count_total * 22, station_max_power_kw_proxy * station_diversity_factor), 10)`.",
            f"- Transformer capacity uses the sum of attached station capacities with a {int((1 - TRANSFORMER_DIVERSITY_FACTOR) * 100)}% diversity margin before rounding to the next 50 kW.",
            "- All transformer and feeder IDs here are synthetic planning assumptions for simulator V1 only.",
            "",
            "## Largest Synthetic Transformers",
            "",
            "| transformer_id | transformer_name | zone_id | stations | assumed_capacity_kw |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for _, row in transformers.sort_values("transformer_capacity_kw_assumed", ascending=False, kind="stable").iterrows():
        lines.append(
            f"| {row['transformer_id']} | {row['transformer_name']} | {row['zone_id']} | "
            f"{int(row['station_count'])} | {int(row['transformer_capacity_kw_assumed'])} |"
        )

    lines.extend(
        [
            "",
            "## Stations Still Needing Location Follow-up",
            "",
        ]
    )
    if followup.empty:
        lines.append("- None.")
    else:
        for _, row in followup.sort_values("station_name", kind="stable").iterrows():
            lines.append(f"- `{row['station_name']}` (`{row['station_id']}`): {row['verification_notes']}")

    lines.extend(
        [
            "",
            "## Explicit Scope Note",
            "- This Dundee zone and transformer layer is a simulator-ready abstraction for V1 and is not intended to represent verified utility transformer placements, feeder routes, or DNO asset names.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Build the Dundee spatial workflow and synthetic simulator topology."""

    args = build_parser().parse_args()
    configure_logging(args.log_level)

    output_paths = [
        args.overrides_csv,
        args.verified_locations_csv,
        args.zones_csv,
        args.station_zone_map_csv,
        args.transformers_csv,
        args.transformer_station_map_csv,
        args.station_capacity_assumptions_csv,
        args.zone_map_html,
        args.zone_map_png,
        args.location_review_summary_md,
        args.zone_design_notes_md,
    ]
    ensure_output_dirs(output_paths)

    review_map_paths = [Path(path) for path in args.review_map_paths]
    missing_review_maps = [path for path in review_map_paths if not path.exists()]
    if missing_review_maps:
        raise FileNotFoundError(f"Missing Dundee review-map artifacts: {missing_review_maps}")

    stations = load_station_inputs(args.station_master, args.station_locations, args.station_catalog_geojson)
    overrides = refresh_override_workflow(stations, args.overrides_csv)
    verified_locations = build_verified_locations(stations, overrides)
    zone_map = build_zone_map(stations)
    transformer_map = build_transformer_map(stations, zone_map)
    station_capacity_assumptions = build_station_capacity_assumptions(
        stations,
        verified_locations,
        zone_map,
        transformer_map,
    )
    zones = build_zones(verified_locations, station_capacity_assumptions)
    transformers = build_transformers(verified_locations, station_capacity_assumptions, transformer_map)

    station_zone_map = zone_map.merge(stations[["station_id", "station_name"]], on="station_id", how="left")
    transformer_station_map = transformer_map.merge(
        station_capacity_assumptions[
            ["station_id", "station_name", "station_capacity_kw_assumed", "zone_id", "transformer_id"]
        ],
        on=["station_id", "zone_id", "transformer_id"],
        how="left",
    )
    stations_for_map = station_capacity_assumptions.merge(
        stations[["station_id", "postcode_mode", "sessions_total"]],
        on="station_id",
        how="left",
    ).merge(
        verified_locations[["station_id", "final_latitude", "final_longitude"]],
        on="station_id",
        how="left",
    )

    verified_locations.to_csv(args.verified_locations_csv, index=False)
    zones.to_csv(args.zones_csv, index=False)
    station_zone_map.to_csv(args.station_zone_map_csv, index=False)
    transformers.to_csv(args.transformers_csv, index=False)
    transformer_station_map.to_csv(args.transformer_station_map_csv, index=False)
    station_capacity_assumptions.to_csv(args.station_capacity_assumptions_csv, index=False)

    build_zone_transformer_map_html(stations_for_map, transformers, args.zone_map_html)
    build_zone_transformer_map_png(stations_for_map, transformers, args.zone_map_png)
    write_location_review_summary(verified_locations, args.overrides_csv, review_map_paths, args.location_review_summary_md)
    write_zone_design_notes(zones, transformers, verified_locations, args.zone_design_notes_md)

    verified_count = int(verified_locations["verification_status"].isin(["accepted_current", "manually_overridden"]).sum())
    followup_count = int(verified_locations["verification_status"].eq("needs_followup").sum())
    print(f"verified_stations={verified_count}")
    print(f"stations_needing_followup={followup_count}")
    print(f"zones={len(zones)}")
    print(f"transformers={len(transformers)}")
    for path in output_paths:
        print(path.as_posix())


if __name__ == "__main__":
    main()
