"""Filesystem repository for feeder-aligned RL exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .contracts import FeederAction


class DigitalTwinFeederRLRepository:
    """Load the DigitalTwin feeder RL package produced by the export script."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir).resolve()

    def load_manifest(self) -> dict[str, Any]:
        path = self.data_dir / "manifest.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def load_action_catalog_frame(self) -> pd.DataFrame:
        frame = self._read_frame("feeder_ev_action_catalog")
        required = {"station_id", "secondary_area_id", "demand_point_id", "node_id"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"feeder_ev_action_catalog is missing columns: {', '.join(missing)}")
        return frame

    def load_actions(self) -> list[FeederAction]:
        frame = self.load_action_catalog_frame()
        return [self._row_to_action(row) for row in frame.to_dict(orient="records")]

    def load_request_priors(self) -> pd.DataFrame:
        try:
            return self._read_frame("feeder_request_priors")
        except FileNotFoundError:
            return pd.DataFrame()

    def load_grid_replay(self) -> pd.DataFrame:
        try:
            return self._read_frame("feeder_grid_advisory_replay")
        except FileNotFoundError:
            return pd.DataFrame()

    def load_feature_stats(self) -> dict[str, Any]:
        path = self.data_dir / "feature_stats.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_frame(self, stem: str) -> pd.DataFrame:
        parquet_path = self.data_dir / f"{stem}.parquet"
        csv_path = self.data_dir / f"{stem}.csv"
        if parquet_path.exists():
            return pd.read_parquet(parquet_path)
        if csv_path.exists():
            return pd.read_csv(csv_path)
        raise FileNotFoundError(f"Missing feeder RL artifact: {parquet_path} or {csv_path}")

    @staticmethod
    def _row_to_action(row: dict[str, Any]) -> FeederAction:
        metadata = {
            key: value
            for key, value in row.items()
            if key
            not in {
                "station_id",
                "secondary_area_id",
                "demand_point_id",
                "node_id",
                "p_base_kw",
                "public_ev_capacity_kw",
                "charger_kw",
                "connector_type",
                "latitude",
                "longitude",
                "x",
                "y",
                "truth_status",
                "source_system",
            }
        }
        return FeederAction(
            station_id=str(row["station_id"]),
            secondary_area_id=str(row["secondary_area_id"]),
            demand_point_id=str(row["demand_point_id"]),
            node_id=str(row["node_id"]),
            p_base_kw=_as_float(row.get("p_base_kw"), 0.0),
            public_ev_capacity_kw=max(_as_float(row.get("public_ev_capacity_kw"), 22.0), 0.0),
            charger_kw=max(_as_float(row.get("charger_kw"), 22.0), 0.0),
            connector_type=str(row.get("connector_type") or "ac").lower(),
            latitude=_optional_float(row.get("latitude")),
            longitude=_optional_float(row.get("longitude")),
            x=_optional_float(row.get("x")),
            y=_optional_float(row.get("y")),
            truth_status=str(row.get("truth_status") or "feeder_aligned"),
            source_system=str(row.get("source_system") or "digitaltwin_phase39"),
            metadata=metadata,
        )


def _optional_float(value: Any) -> float | None:
    result = _as_float(value, float("nan"))
    return None if result != result else result


def _as_float(value: Any, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return default if result != result else result


__all__ = ["DigitalTwinFeederRLRepository"]
