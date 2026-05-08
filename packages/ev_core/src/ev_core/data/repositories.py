"""Repository helpers for processed Dundee simulator datasets."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from ev_core.topology.scenarios import TopologyScenario, load_topology_scenario


@dataclass(frozen=True)
class DatasetHandle:
    """Lightweight pointer to a named dataset artifact."""

    name: str
    path: Path
    format_hint: str = "unknown"


@dataclass(frozen=True)
class DundeeDataPaths:
    """Resolved filesystem paths for the Dundee simulator artifacts."""

    repo_root: Path
    station_master: Path
    station_access_overrides: Path
    chargepoint_master: Path
    station_locations_verified: Path
    zones: Path
    station_zone_map: Path
    transformers: Path
    transformer_station_map: Path
    station_capacity_assumptions: Path
    request_replay_2023: Path
    request_replay_2024: Path
    request_generator_params: Path
    background_load_15min: Path
    price_table_15min: Path
    pv_profile_15min: Path
    model_ready_csv: Path
    topology_scenarios_dir: Path
    default_topology_scenario: Path

    @classmethod
    def from_repo_root(cls, repo_root: str | Path) -> "DundeeDataPaths":
        """Build Dundee dataset paths from the repository root."""

        root = Path(repo_root).resolve()
        processed = root / "data" / "processed"
        return cls(
            repo_root=root,
            station_master=processed / "station_master.csv",
            station_access_overrides=processed / "station_access_overrides.csv",
            chargepoint_master=processed / "chargepoint_master.csv",
            station_locations_verified=processed / "station_locations_verified.csv",
            zones=processed / "zones.csv",
            station_zone_map=processed / "station_zone_map.csv",
            transformers=processed / "transformers.csv",
            transformer_station_map=processed / "transformer_station_map.csv",
            station_capacity_assumptions=processed / "station_capacity_assumptions.csv",
            request_replay_2023=processed / "request_replay_2023.csv",
            request_replay_2024=processed / "request_replay_2024.csv",
            request_generator_params=processed / "request_generator_params.json",
            background_load_15min=processed / "background_load_15min.csv",
            price_table_15min=processed / "price_table_15min.csv",
            pv_profile_15min=processed / "pv_profile_15min.csv",
            model_ready_csv=root / "data" / "interim" / "dundee_sessions_model_ready.csv",
            topology_scenarios_dir=processed / "topology_scenarios",
            default_topology_scenario=processed / "topology_scenarios" / "dundee_synthetic_v1.json",
        )


@dataclass(frozen=True)
class DundeeDataBundle:
    """Loaded Dundee datasets used by the standalone simulator runtime."""

    stations: pd.DataFrame
    transformers: pd.DataFrame
    zones: pd.DataFrame
    chargepoints: pd.DataFrame
    replay_requests_2023: pd.DataFrame
    replay_requests_2024: pd.DataFrame
    request_generator_params: dict[str, Any]
    background_load: pd.DataFrame
    price_table: pd.DataFrame
    pv_profile: pd.DataFrame


class DatasetRepository(Protocol):
    """Protocol for dataset catalogs and storage backends."""

    def get(self, name: str) -> DatasetHandle:
        """Return the dataset handle for the requested artifact name."""

    def list(self) -> list[DatasetHandle]:
        """Return the known dataset handles."""


class FileSystemDatasetRepository:
    """Simple filesystem-backed dataset lookup."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def get(self, name: str) -> DatasetHandle:
        path = self.root / name
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")
        return DatasetHandle(name=name, path=path, format_hint=path.suffix.lstrip(".") or "unknown")

    def list(self) -> list[DatasetHandle]:
        handles: list[DatasetHandle] = []
        for path in sorted(self.root.glob("*")):
            if path.is_file():
                handles.append(DatasetHandle(name=path.name, path=path, format_hint=path.suffix.lstrip(".") or "unknown"))
        return handles


class DundeeSimulationRepository:
    """Filesystem repository that loads Dundee simulator inputs with safe fallbacks."""

    ACCESS_BOOLEAN_COLUMNS = (
        "is_public",
        "is_fleet_only",
        "requires_membership",
        "needs_followup",
        "exclude_from_recommendations",
    )
    ACCESS_DEFAULTS = {
        "is_public": True,
        "is_fleet_only": False,
        "requires_membership": False,
        "needs_followup": False,
        "exclude_from_recommendations": False,
    }
    ACCESS_OVERRIDE_COLUMNS = (
        "station_id",
        "is_public",
        "is_fleet_only",
        "requires_membership",
        "needs_followup",
        "exclude_from_recommendations",
        "access_notes",
        "review_status",
        "review_source",
    )

    def __init__(self, repo_root: str | Path) -> None:
        self.paths = DundeeDataPaths.from_repo_root(repo_root)

    def load_bundle(self) -> DundeeDataBundle:
        """Load the Dundee datasets needed by the standalone simulator runtime."""

        stations = self.load_station_table()
        transformers = pd.read_csv(self.paths.transformers)
        zones = pd.read_csv(self.paths.zones)
        chargepoints = pd.read_csv(self.paths.chargepoint_master)
        replay_requests_2023 = self._load_replay_table(self.paths.request_replay_2023)
        replay_requests_2024 = self._load_replay_table(self.paths.request_replay_2024)
        request_generator_params = json.loads(self.paths.request_generator_params.read_text(encoding="utf-8"))
        background_load = self._load_background_load(transformers)
        price_table = self._load_price_table()
        pv_profile = self._load_pv_profile()
        return DundeeDataBundle(
            stations=stations,
            transformers=transformers,
            zones=zones,
            chargepoints=chargepoints,
            replay_requests_2023=replay_requests_2023,
            replay_requests_2024=replay_requests_2024,
            request_generator_params=request_generator_params,
            background_load=background_load,
            price_table=price_table,
            pv_profile=pv_profile,
        )

    def load_station_table(self) -> pd.DataFrame:
        """Load and merge the Dundee station topology table, with capacity fallback logic."""

        station_master = pd.read_csv(self.paths.station_master)
        verified_locations = pd.read_csv(self.paths.station_locations_verified)
        station_zone_map = pd.read_csv(self.paths.station_zone_map)
        transformer_station_map = pd.read_csv(self.paths.transformer_station_map)
        capacity = self._safe_load_station_capacity_assumptions()

        stations = station_master.merge(
            verified_locations[
                [
                    "station_id",
                    "final_latitude",
                    "final_longitude",
                    "verification_status",
                    "location_confidence_final",
                ]
            ],
            on="station_id",
            how="left",
        ).merge(
            station_zone_map[["station_id", "zone_id", "zone_name"]],
            on="station_id",
            how="left",
        ).merge(
            transformer_station_map[
                [
                    "station_id",
                    "transformer_id",
                    "transformer_name",
                    "station_capacity_kw_assumed",
                ]
            ],
            on="station_id",
            how="left",
        )

        if capacity is not None:
            stations = stations.drop(columns=["station_capacity_kw_assumed"], errors="ignore").merge(
                capacity[["station_id", "station_capacity_kw_assumed"]],
                on="station_id",
                how="left",
            )
        stations["latitude"] = pd.to_numeric(stations["final_latitude"], errors="coerce")
        stations["longitude"] = pd.to_numeric(stations["final_longitude"], errors="coerce")
        stations["station_capacity_kw_assumed"] = pd.to_numeric(stations["station_capacity_kw_assumed"], errors="coerce")
        stations = self._apply_station_access_overrides(stations)
        return stations.sort_values(["zone_id", "station_name"], kind="stable").reset_index(drop=True)

    def _apply_station_access_overrides(self, stations: pd.DataFrame) -> pd.DataFrame:
        stations = self._ensure_access_columns(stations.copy())
        if not self.paths.station_access_overrides.exists():
            return stations

        overrides = pd.read_csv(self.paths.station_access_overrides, dtype=str).fillna("")
        missing_columns = [column for column in self.ACCESS_OVERRIDE_COLUMNS if column not in overrides.columns]
        if missing_columns:
            raise ValueError(f"station access override file is missing columns: {', '.join(missing_columns)}")

        station_ids = set(stations["station_id"].astype(str))
        override_ids = set(overrides["station_id"].astype(str))
        unknown_ids = sorted(override_ids - station_ids)
        if unknown_ids:
            raise ValueError(f"station access override file references unknown station_id values: {', '.join(unknown_ids)}")

        overrides = overrides[list(self.ACCESS_OVERRIDE_COLUMNS)].copy()
        for column in self.ACCESS_BOOLEAN_COLUMNS:
            overrides[column] = overrides[column].map(lambda value, default=self.ACCESS_DEFAULTS[column]: self._coerce_bool(value, default))
        overrides = overrides.rename(
            columns={
                "review_status": "access_review_status",
                "review_source": "access_review_source",
            }
        )
        for column in ("access_notes", "access_review_status", "access_review_source"):
            overrides[column] = overrides[column].map(self._clean_optional_text)

        stations = stations.merge(overrides, on="station_id", how="left", suffixes=("", "_override"))
        for column in self.ACCESS_BOOLEAN_COLUMNS:
            override_column = f"{column}_override"
            stations[column] = stations[override_column].where(stations[override_column].notna(), stations[column])
            stations = stations.drop(columns=[override_column])
        for column in ("access_notes", "access_review_status", "access_review_source"):
            override_column = f"{column}_override"
            if override_column in stations.columns:
                stations[column] = stations[override_column].where(stations[override_column].notna(), stations[column])
                stations = stations.drop(columns=[override_column])
        return self._ensure_access_columns(stations)

    def _ensure_access_columns(self, stations: pd.DataFrame) -> pd.DataFrame:
        for column, default in self.ACCESS_DEFAULTS.items():
            if column not in stations.columns:
                stations[column] = default
            stations[column] = stations[column].map(lambda value, default=default: self._coerce_bool(value, default)).astype(object)
        for column in ("access_notes", "access_review_status", "access_review_source"):
            if column not in stations.columns:
                stations[column] = None
            stations[column] = stations[column].map(self._clean_optional_text)
        return stations

    @staticmethod
    def _coerce_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if isinstance(value, float) and math.isnan(value):
                return default
            return bool(value)
        normalized = str(value).strip().lower()
        if normalized in {"", "nan", "none", "null"}:
            return default
        if normalized in {"1", "true", "t", "yes", "y"}:
            return True
        if normalized in {"0", "false", "f", "no", "n"}:
            return False
        return default

    @staticmethod
    def _clean_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, float) and math.isnan(value):
            return None
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null"}:
            return None
        return text

    def get_replay_requests(self, year: int) -> pd.DataFrame:
        """Return the Dundee replay requests for the requested year."""

        if year == 2023:
            return self._load_replay_table(self.paths.request_replay_2023)
        if year == 2024:
            return self._load_replay_table(self.paths.request_replay_2024)
        raise ValueError(f"Replay year not supported: {year}")

    def load_topology_scenario(self, scenario_id_or_path: str | Path) -> TopologyScenario:
        """Load a topology scenario by ID from processed data or by explicit JSON path."""

        scenario_ref = Path(scenario_id_or_path)
        if scenario_ref.suffix:
            scenario_path = scenario_ref
            if not scenario_path.is_absolute():
                scenario_path = self.paths.repo_root / scenario_path
        else:
            scenario_path = self.paths.topology_scenarios_dir / f"{scenario_id_or_path}.json"
        return load_topology_scenario(scenario_path)

    def _load_replay_table(self, path: Path) -> pd.DataFrame:
        try:
            frame = pd.read_csv(
                path,
                parse_dates=[
                    "arrival_ts",
                    "arrival_slot",
                    "latest_finish_ts",
                    "latest_finish_slot",
                ],
            )
            return frame.sort_values(["arrival_slot", "request_id"], kind="stable").reset_index(drop=True)
        except (UnicodeDecodeError, pd.errors.ParserError):
            year = 2024 if "2024" in path.name else 2023
            return self._build_replay_from_model_ready(year)

    def _safe_load_station_capacity_assumptions(self) -> pd.DataFrame | None:
        """Load the station capacity table or derive it from station master metadata."""

        try:
            capacity = pd.read_csv(self.paths.station_capacity_assumptions)
            if "station_capacity_kw_assumed" in capacity.columns:
                return capacity
        except UnicodeDecodeError:
            pass
        except pd.errors.ParserError:
            pass
        return self._derive_station_capacity_assumptions()

    def _derive_station_capacity_assumptions(self) -> pd.DataFrame:
        """Fallback capacity derivation aligned with the Dundee topology scaffolding."""

        station_master = pd.read_csv(self.paths.station_master)
        station_zone_map = pd.read_csv(self.paths.station_zone_map)
        transformer_station_map = pd.read_csv(self.paths.transformer_station_map)

        def connector_diversity(connector_mix_total: str) -> float:
            values = {item.strip() for item in str(connector_mix_total).split(";") if item.strip()}
            if "ultra_rapid" in values:
                return 0.85
            if "rapid" in values:
                return 0.90
            return 1.0

        derived = station_master.copy()
        derived["baseline_port_capacity_kw"] = pd.to_numeric(derived["cp_count_total"], errors="coerce").fillna(0) * 22
        derived["station_diversity_factor"] = derived["connector_mix_total"].map(connector_diversity)
        derived["station_capacity_kw_assumed"] = (
            pd.concat(
                [
                    derived["baseline_port_capacity_kw"],
                    pd.to_numeric(derived["station_max_power_kw_proxy"], errors="coerce").fillna(0)
                    * derived["station_diversity_factor"],
                ],
                axis=1,
            )
            .max(axis=1)
            .apply(lambda value: int((max(float(value), 10.0) + 9.999) // 10) * 10)
        )
        derived = derived.merge(station_zone_map[["station_id", "zone_id", "zone_name"]], on="station_id", how="left")
        derived = derived.merge(
            transformer_station_map[["station_id", "transformer_id", "transformer_name"]],
            on="station_id",
            how="left",
        )
        return derived

    def _build_replay_from_model_ready(self, year: int) -> pd.DataFrame:
        """Fallback replay derivation from the Dundee model-ready sessions."""

        model_ready = pd.read_csv(
            self.paths.model_ready_csv,
            parse_dates=["arrival_ts", "approx_departure_ts"],
        )
        model_ready = model_ready[model_ready["arrival_ts"].dt.year == year].copy()
        stations = self.load_station_table()[
            [
                "station_id",
                "station_name",
                "zone_id",
                "transformer_id",
            ]
        ].drop_duplicates()
        replay = model_ready.merge(stations, on=["station_id", "station_name"], how="left", suffixes=("", "_station"))
        replay["arrival_slot"] = replay["arrival_ts"].dt.floor("15min")
        replay["latest_finish_ts"] = replay["approx_departure_ts"]
        replay["latest_finish_slot"] = replay["latest_finish_ts"].dt.ceil("15min")
        replay["user_preference_mode"] = replay.apply(
            lambda row: self._infer_preference_mode(str(row["session_id"]), str(row["connector_type"])),
            axis=1,
        )
        replay["charger_type_preference"] = replay["connector_type"].map(
            {"ac": "AC", "rapid": "Rapid", "ultra_rapid": "Rapid"}
        ).fillna("Any")
        replay["requested_duration_minutes"] = replay.apply(
            lambda row: self._derive_requested_duration_minutes(
                energy_kwh=float(row["energy_kwh"]),
                connector_limit_kw=float(row["assumed_connector_limit_kw"]),
                arrival_slot=row["arrival_slot"].to_pydatetime(),
                latest_finish_slot=row["latest_finish_slot"].to_pydatetime(),
                preference_mode=str(row["user_preference_mode"]),
            ),
            axis=1,
        )
        replay = replay[
            [
                "session_id",
                "arrival_ts",
                "arrival_slot",
                "zone_id",
                "transformer_id",
                "station_id",
                "energy_kwh",
                "requested_duration_minutes",
                "latest_finish_ts",
                "latest_finish_slot",
                "user_preference_mode",
                "charger_type_preference",
                "source_year",
                "station_name",
                "cp_id",
                "connector_type",
                "assumed_connector_limit_kw",
            ]
        ].rename(
            columns={
                "session_id": "source_session_id",
                "energy_kwh": "requested_energy_kwh",
            }
        )
        replay["request_year"] = year
        replay = replay.sort_values(["arrival_slot", "source_session_id"], kind="stable").reset_index(drop=True)
        replay["request_id"] = [
            f"dundee_replay_{year}_{idx:06d}"
            for idx in range(1, len(replay) + 1)
        ]
        ordered_columns = [
            "request_id",
            "source_session_id",
            "arrival_ts",
            "arrival_slot",
            "zone_id",
            "transformer_id",
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
        ]
        return replay[ordered_columns]

    def _infer_preference_mode(self, session_id: str, connector_type: str) -> str:
        distribution = {
            "ac": {"closest": 0.50, "cheapest": 0.35, "fastest": 0.15},
            "rapid": {"closest": 0.25, "cheapest": 0.15, "fastest": 0.60},
            "ultra_rapid": {"closest": 0.15, "cheapest": 0.10, "fastest": 0.75},
        }.get(connector_type, {"closest": 0.40, "cheapest": 0.30, "fastest": 0.30})
        digest = hashlib.sha256(f"{session_id}|{connector_type}".encode("utf-8")).hexdigest()
        bucket = int(digest[:12], 16) / float(16**12)
        cumulative = 0.0
        for mode, share in distribution.items():
            cumulative += share
            if bucket <= cumulative:
                return mode
        return "fastest"

    def _derive_requested_duration_minutes(
        self,
        *,
        energy_kwh: float,
        connector_limit_kw: float,
        arrival_slot: datetime,
        latest_finish_slot: datetime,
        preference_mode: str,
    ) -> int:
        aligned_window_minutes = int((latest_finish_slot - arrival_slot).total_seconds() // 60)
        technical_minutes = max((energy_kwh / max(connector_limit_kw, 1.0)) * 60.0, 1.0)
        technical_15 = int(math.ceil(technical_minutes / 15.0) * 15)
        slack = max(aligned_window_minutes - technical_15, 0)
        factor = {"fastest": 0.0, "closest": 0.35, "cheapest": 0.70}.get(preference_mode, 0.35)
        return max(15, technical_15 + int(math.floor(slack * factor / 15.0) * 15))

    def _load_background_load(self, transformers: pd.DataFrame) -> pd.DataFrame:
        try:
            return pd.read_csv(self.paths.background_load_15min, parse_dates=["timestamp"])
        except (FileNotFoundError, UnicodeDecodeError, pd.errors.ParserError):
            return self._build_background_load(transformers)

    def _load_price_table(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.paths.price_table_15min, parse_dates=["timestamp"])
        except (UnicodeDecodeError, pd.errors.ParserError):
            return self._build_price_table()

    def _load_pv_profile(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.paths.pv_profile_15min, parse_dates=["timestamp"])
        except (UnicodeDecodeError, pd.errors.ParserError):
            return self._build_pv_profile()

    def _build_background_load(self, transformers: pd.DataFrame) -> pd.DataFrame:
        timeline = pd.DataFrame({"timestamp": pd.date_range("2023-01-01 00:00:00", "2024-12-31 23:45:00", freq="15min")})
        timeline["date"] = timeline["timestamp"].dt.date.astype(str)
        timeline["year"] = timeline["timestamp"].dt.year.astype("int64")
        timeline["month"] = timeline["timestamp"].dt.month.astype("int64")
        timeline["weekday_name"] = timeline["timestamp"].dt.day_name()
        timeline["is_weekend"] = timeline["timestamp"].dt.dayofweek >= 5
        timeline["hour"] = timeline["timestamp"].dt.hour.astype("int64")
        timeline["minute"] = timeline["timestamp"].dt.minute.astype("int64")
        timeline["quarter_hour_slot"] = ((timeline["hour"] * 60) + timeline["minute"]) // 15
        weekday_levels = pd.Series(
            np.select(
                [
                    timeline["hour"].between(0, 5),
                    timeline["hour"].between(6, 8),
                    timeline["hour"].between(9, 15),
                    timeline["hour"].between(16, 20),
                ],
                [0.18, 0.31, 0.28, 0.42],
                default=0.24,
            )
        )
        weekend_levels = pd.Series(
            np.select(
                [
                    timeline["hour"].between(0, 6),
                    timeline["hour"].between(7, 10),
                    timeline["hour"].between(11, 17),
                    timeline["hour"].between(18, 21),
                ],
                [0.16, 0.24, 0.29, 0.34],
                default=0.22,
            )
        )
        timeline["base_background_pu"] = weekend_levels.where(timeline["is_weekend"], weekday_levels)
        month_multiplier = {
            1: 1.08, 2: 1.06, 3: 1.03, 4: 1.00, 5: 0.98, 6: 0.97,
            7: 0.98, 8: 0.99, 9: 1.00, 10: 1.02, 11: 1.05, 12: 1.08,
        }
        zone_multiplier = {
            "zone_central_waterfront": 1.08,
            "zone_west_lochee": 0.98,
            "zone_north_inner": 0.95,
            "zone_east_corridor": 1.00,
        }
        timeline["month_multiplier"] = timeline["month"].map(month_multiplier).astype(float)
        timeline["quarter_adjustment"] = timeline["minute"].map({0: -0.010, 15: 0.000, 30: 0.008, 45: 0.004}).astype(float)
        transformer_base = transformers[["transformer_id", "transformer_name", "zone_id", "transformer_capacity_kw_assumed"]].copy()
        transformer_base["zone_background_multiplier"] = transformer_base["zone_id"].map(zone_multiplier).fillna(1.0)
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
                "background_load_pu",
                "background_load_kw",
            ]
        ]

    def _build_price_table(self) -> pd.DataFrame:
        frame = pd.DataFrame({"timestamp": pd.date_range("2023-01-01 00:00:00", "2024-12-31 23:45:00", freq="15min")})
        frame["date"] = frame["timestamp"].dt.date.astype(str)
        frame["year"] = frame["timestamp"].dt.year.astype("int64")
        frame["month"] = frame["timestamp"].dt.month.astype("int64")
        frame["weekday_name"] = frame["timestamp"].dt.day_name()
        frame["is_weekend"] = frame["timestamp"].dt.dayofweek >= 5
        frame["hour"] = frame["timestamp"].dt.hour.astype("int64")
        frame["quarter_hour_slot"] = ((frame["hour"] * 60) + frame["timestamp"].dt.minute) // 15
        weekday_price = pd.Series(
            np.select(
                [frame["hour"].between(0, 5), frame["hour"].between(6, 15), frame["hour"].between(16, 20)],
                [0.18, 0.24, 0.34],
                default=0.22,
            )
        )
        weekend_price = pd.Series(
            np.select(
                [frame["hour"].between(0, 6), frame["hour"].between(7, 15), frame["hour"].between(16, 20)],
                [0.17, 0.21, 0.25],
                default=0.19,
            )
        )
        frame["price_gbp_per_kwh"] = weekend_price.where(frame["is_weekend"], weekday_price)
        return frame

    def _build_pv_profile(self) -> pd.DataFrame:
        frame = pd.DataFrame({"timestamp": pd.date_range("2023-01-01 00:00:00", "2024-12-31 23:45:00", freq="15min")})
        frame["date"] = frame["timestamp"].dt.date.astype(str)
        frame["year"] = frame["timestamp"].dt.year.astype("int64")
        frame["month"] = frame["timestamp"].dt.month.astype("int64")
        frame["hour"] = frame["timestamp"].dt.hour.astype("int64")
        frame["minute"] = frame["timestamp"].dt.minute.astype("int64")
        frame["quarter_hour_slot"] = ((frame["hour"] * 60) + frame["minute"]) // 15
        daylight_hours = {1: 8.0, 2: 9.5, 3: 11.5, 4: 13.5, 5: 15.5, 6: 16.5, 7: 16.0, 8: 14.5, 9: 12.5, 10: 10.5, 11: 9.0, 12: 8.0}
        seasonal_peak = {1: 0.38, 2: 0.46, 3: 0.58, 4: 0.72, 5: 0.84, 6: 0.92, 7: 0.90, 8: 0.80, 9: 0.66, 10: 0.54, 11: 0.42, 12: 0.34}
        frame["daylight_hours"] = frame["month"].map(daylight_hours).astype(float)
        frame["seasonal_peak_cf"] = frame["month"].map(seasonal_peak).astype(float)
        hour_decimal = frame["hour"] + (frame["minute"] / 60.0)
        sunrise = 12.5 - (frame["daylight_hours"] / 2.0)
        sunset = 12.5 + (frame["daylight_hours"] / 2.0)
        daylight_position = (hour_decimal - sunrise) / (sunset - sunrise)
        shape = np.where(
            (daylight_position >= 0.0) & (daylight_position <= 1.0),
            np.sin(np.pi * daylight_position) ** 1.5,
            0.0,
        )
        frame["pv_generation_kw_per_mw"] = (shape * frame["seasonal_peak_cf"] * 1000).round(3)
        return frame


__all__ = [
    "DatasetHandle",
    "DatasetRepository",
    "DundeeDataBundle",
    "DundeeDataPaths",
    "DundeeSimulationRepository",
    "FileSystemDatasetRepository",
]
