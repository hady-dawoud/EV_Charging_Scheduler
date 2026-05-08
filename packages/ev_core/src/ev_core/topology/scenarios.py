"""Lightweight topology scenario definitions and loaders."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TransformerScenario:
    transformer_id: str
    transformer_name: str
    zone_id: str
    capacity_kw: float
    attached_station_ids: tuple[str, ...] = ()
    latitude: float | None = None
    longitude: float | None = None
    capacity_derating_factor: float = 1.0
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.transformer_id:
            raise ValueError("TransformerScenario transformer_id is required")
        if self.capacity_kw <= 0:
            raise ValueError(f"TransformerScenario {self.transformer_id} capacity_kw must be positive")
        if self.capacity_derating_factor <= 0:
            raise ValueError(f"TransformerScenario {self.transformer_id} capacity_derating_factor must be positive")

    @property
    def effective_capacity_kw(self) -> float:
        """Capacity after static scenario derating."""

        return float(self.capacity_kw) * float(self.capacity_derating_factor)


@dataclass(frozen=True)
class TopologyScenario:
    scenario_id: str
    scenario_name: str
    source: str
    transformers: tuple[TransformerScenario, ...]
    station_to_transformer: dict[str, str] = field(default_factory=dict)
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("TopologyScenario scenario_id is required")
        if not self.transformers:
            raise ValueError(f"TopologyScenario {self.scenario_id} must define at least one transformer")
        transformer_ids = [transformer.transformer_id for transformer in self.transformers]
        duplicates = sorted({value for value in transformer_ids if transformer_ids.count(value) > 1})
        if duplicates:
            raise ValueError(f"TopologyScenario {self.scenario_id} has duplicate transformer_id values: {', '.join(duplicates)}")


class TopologyScenarioProvider:
    """Apply an optional topology scenario to station and transformer tables."""

    def __init__(self, scenario: TopologyScenario | None = None):
        self.scenario = scenario

    def apply_to_station_rows(self, stations_df):
        """Return station rows with scenario transformer mappings applied."""

        if self.scenario is None:
            return stations_df
        if "station_id" not in stations_df.columns:
            raise ValueError("station rows must include a station_id column")
        stations = stations_df.copy()
        station_ids = set(stations["station_id"].astype(str))
        attached_station_ids = {
            station_id
            for transformer in self.scenario.transformers
            for station_id in transformer.attached_station_ids
        }
        unknown_stations = sorted((set(self.scenario.station_to_transformer) | attached_station_ids) - station_ids)
        if unknown_stations:
            raise ValueError(f"topology scenario references unknown station_id values: {', '.join(unknown_stations)}")

        known_transformers = {transformer.transformer_id for transformer in self.scenario.transformers}
        unknown_transformers = sorted(set(self.scenario.station_to_transformer.values()) - known_transformers)
        if unknown_transformers:
            raise ValueError(f"topology scenario references unknown transformer_id values: {', '.join(unknown_transformers)}")

        if self.scenario.station_to_transformer:
            stations["station_id"] = stations["station_id"].astype(str)
            mapped_transformers = stations["station_id"].map(self.scenario.station_to_transformer)
            stations["transformer_id"] = mapped_transformers.where(mapped_transformers.notna(), stations["transformer_id"])
        return stations

    def transformer_rows(self, default_transformers_df, station_rows=None):
        """Return transformer rows, using scenario definitions when configured."""

        if self.scenario is None:
            return default_transformers_df
        import pandas as pd

        rows: list[dict[str, Any]] = []
        station_counts: dict[str, int] = {}
        if station_rows is not None and not station_rows.empty:
            station_counts = station_rows.groupby("transformer_id")["station_id"].count().to_dict()

        for transformer in self.scenario.transformers:
            rows.append(
                {
                    "transformer_id": transformer.transformer_id,
                    "transformer_name": transformer.transformer_name,
                    "zone_id": transformer.zone_id,
                    "transformer_capacity_kw_assumed": transformer.effective_capacity_kw,
                    "capacity_derating_factor": transformer.capacity_derating_factor,
                    "station_count": int(station_counts.get(transformer.transformer_id, len(transformer.attached_station_ids))),
                    "latitude": transformer.latitude,
                    "longitude": transformer.longitude,
                    "topology_source": self.scenario.source,
                    "notes": transformer.notes or self.scenario.notes,
                }
            )
        # TODO: add time-varying capacity profiles once scenario evaluation needs them.
        return pd.DataFrame(rows)


def load_topology_scenario(path: str | Path) -> TopologyScenario:
    """Load a topology scenario JSON file."""

    scenario_path = Path(path)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Topology scenario file not found: {scenario_path}")
    if scenario_path.suffix.lower() != ".json":
        raise ValueError(f"Topology scenario files must be JSON for now: {scenario_path}")
    payload = json.loads(scenario_path.read_text(encoding="utf-8"))
    return topology_scenario_from_dict(payload, source_path=scenario_path)


def topology_scenario_from_dict(payload: dict[str, Any], *, source_path: Path | None = None) -> TopologyScenario:
    required = ("scenario_id", "scenario_name", "source", "transformers", "station_to_transformer")
    missing = [field_name for field_name in required if field_name not in payload]
    if missing:
        location = f" in {source_path}" if source_path is not None else ""
        raise ValueError(f"topology scenario{location} missing required fields: {', '.join(missing)}")

    transformers = tuple(
        TransformerScenario(
            transformer_id=str(row["transformer_id"]),
            transformer_name=str(row["transformer_name"]),
            zone_id=str(row["zone_id"]),
            capacity_kw=float(row["capacity_kw"]),
            attached_station_ids=tuple(str(value) for value in row.get("attached_station_ids", ())),
            latitude=_optional_float(row.get("latitude")),
            longitude=_optional_float(row.get("longitude")),
            capacity_derating_factor=float(row.get("capacity_derating_factor", 1.0)),
            notes=_optional_text(row.get("notes")),
        )
        for row in payload["transformers"]
    )
    return TopologyScenario(
        scenario_id=str(payload["scenario_id"]),
        scenario_name=str(payload["scenario_name"]),
        source=str(payload["source"]),
        transformers=transformers,
        station_to_transformer={str(key): str(value) for key, value in dict(payload["station_to_transformer"]).items()},
        notes=_optional_text(payload.get("notes")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "TopologyScenario",
    "TopologyScenarioProvider",
    "TransformerScenario",
    "load_topology_scenario",
    "topology_scenario_from_dict",
]
