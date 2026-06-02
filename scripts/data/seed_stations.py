from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"

for path in (REPO_ROOT, API_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.db.session import SessionLocal
from app.models.station import Station
from app.repositories.stations_repository import upsert_station_record


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value


def clean_bool(value: Any, default: bool = False) -> bool:
    value = clean_value(value)

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}

    return bool(value)


def clean_int(value: Any, default: int = 0) -> int:
    value = clean_value(value)
    return default if value is None else int(value)


def clean_float(value: Any, default: float | None = None) -> float | None:
    value = clean_value(value)
    return default if value is None else float(value)


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(REPO_ROOT / name)


def build_station_rows() -> list[dict[str, Any]]:
    master = load_csv("data/processed/station_master.csv")
    locations = load_csv("data/processed/station_locations_verified.csv")
    zones = load_csv("data/processed/station_zone_map.csv")
    transformers = load_csv("data/processed/transformer_station_map.csv")
    access = load_csv("data/processed/station_access_overrides.csv")

    merged = master.merge(
        locations[
            [
                "station_id",
                "final_latitude",
                "final_longitude",
                "final_location_source",
                "location_confidence_final",
                "needs_followup_flag",
            ]
        ],
        on="station_id",
        how="left",
    )

    merged = merged.merge(
        zones[["station_id", "zone_id"]],
        on="station_id",
        how="left",
        suffixes=("", "_zone"),
    )

    merged = merged.merge(
        transformers[
            [
                "station_id",
                "transformer_id",
                "station_capacity_kw_assumed",
            ]
        ],
        on="station_id",
        how="left",
    )

    merged = merged.merge(
        access[
            [
                "station_id",
                "is_public",
                "is_fleet_only",
                "requires_membership",
                "needs_followup",
                "exclude_from_recommendations",
                "access_notes",
            ]
        ],
        on="station_id",
        how="left",
    )

    rows: list[dict[str, Any]] = []

    for record in merged.to_dict(orient="records"):
        rows.append(
            {
                "station_id": str(record["station_id"]),
                "station_name": str(record["station_name"]),
                "postcode": clean_value(record.get("postcode_mode")),
                "latitude": clean_float(
                    record.get("final_latitude"),
                    clean_float(record.get("latitude"), 0.0),
                ),
                "longitude": clean_float(
                    record.get("final_longitude"),
                    clean_float(record.get("longitude"), 0.0),
                ),
                "zone_id": clean_value(record.get("zone_id")),
                "transformer_id": clean_value(record.get("transformer_id")),
                "cp_count_total": clean_int(record.get("cp_count_total")),
                "connector_mix_total": clean_value(record.get("connector_mix_total")),
                "station_max_power_kw_proxy": clean_float(
                    record.get("station_max_power_kw_proxy")
                ),
                "station_capacity_kw_assumed": clean_float(
                    record.get("station_capacity_kw_assumed")
                ),
                "is_public": clean_bool(record.get("is_public"), default=True),
                "is_fleet_only": clean_bool(record.get("is_fleet_only"), default=False),
                "requires_membership": clean_bool(
                    record.get("requires_membership"),
                    default=False,
                ),
                "exclude_from_recommendations": clean_bool(
                    record.get("exclude_from_recommendations"),
                    default=False,
                ),
                "access_notes": clean_value(record.get("access_notes")),
                "location_source": clean_value(
                    record.get("final_location_source")
                    or record.get("location_source")
                ),
                "location_confidence": clean_value(
                    record.get("location_confidence_final")
                ),
                "needs_followup": clean_bool(
                    record.get("needs_followup")
                    if clean_value(record.get("needs_followup")) is not None
                    else record.get("needs_followup_flag"),
                    default=False,
                ),
                "sessions_total": clean_int(record.get("sessions_total")),
                "energy_total_kwh": clean_float(record.get("energy_total_kwh"), 0.0),
            }
        )

    return rows


def main() -> None:
    rows = build_station_rows()

    with SessionLocal() as db:
        for row in rows:
            upsert_station_record(db, Station(**row))

    print(f"seeded_stations: {len(rows)}")


if __name__ == "__main__":
    main()
