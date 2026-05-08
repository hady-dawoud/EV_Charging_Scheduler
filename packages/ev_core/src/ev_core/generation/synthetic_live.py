"""Generate live-style Dundee charging requests from historical priors."""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.vehicles.profiles import VehicleProfile, get_default_vehicle_profiles


PREFERENCE_FALLBACK = {"closest": 0.4, "cheapest": 0.3, "fastest": 0.3}
TARGET_SOC_WEIGHTS = {80.0: 0.7, 90.0: 0.2, 70.0: 0.1}
GENERATOR_VERSION = "synthetic_live_v1"


@dataclass(frozen=True)
class _StationRecord:
    station_id: str
    station_name: str
    zone_id: str
    latitude: float
    longitude: float
    cp_count_total: int
    connector_mix_total: str
    sessions_total: float


class SyntheticLiveRequestGenerator:
    """Create app-like `ExternalChargingRequest` instances without replaying sessions."""

    def __init__(
        self,
        *,
        request_generator_params: dict[str, Any],
        stations: Sequence[Any],
        vehicle_profiles: Mapping[str, VehicleProfile] | None = None,
        seed: int | str = 42,
    ) -> None:
        self.request_generator_params = dict(request_generator_params)
        self.stations = tuple(self._coerce_station(station) for station in stations)
        if not self.stations:
            raise ValueError("SyntheticLiveRequestGenerator requires at least one station.")
        self.vehicle_profiles = dict(vehicle_profiles or get_default_vehicle_profiles())
        if not self.vehicle_profiles:
            raise ValueError("SyntheticLiveRequestGenerator requires at least one vehicle profile.")
        self.seed = str(seed)

    def generate_one(self, request_timestamp: datetime, index: int = 0) -> ExternalChargingRequest:
        """Generate one deterministic live-style request for the supplied timestamp/index."""

        rng = self._rng("one", request_timestamp.isoformat(), index)
        zone_id = str(self._weighted_choice(self._zone_weights(), rng))
        station = self._choose_anchor_station(zone_id, rng)
        profile = self._choose_vehicle_profile(rng)
        energy_sample = self._sample_summary("requested_energy_kwh_summary", rng, fallback=20.0)
        target_soc = float(self._weighted_choice(TARGET_SOC_WEIGHTS, rng))
        max_gap = max(target_soc - 5.0, 5.0)
        soc_gap = self._clamp((energy_sample / profile.battery_kwh) * 100.0, 10.0, max_gap)
        current_soc = round(target_soc - soc_gap, 3)
        requested_energy_kwh = round(((target_soc - current_soc) / 100.0) * profile.battery_kwh, 3)
        preference_mode = str(self._weighted_choice(self._preference_weights(), rng))
        charger_type = self._choose_charger_type(preference_mode, station, profile, rng)
        duration_minutes = self._sample_summary("requested_duration_minutes_summary", rng, fallback=45.0)
        slack_minutes = self._sample_summary("slack_minutes_summary", rng, fallback=30.0)
        window_minutes = max(int(round((duration_minutes + slack_minutes) / 15.0) * 15), 30)
        latitude, longitude = self._jitter_location(station, rng)
        request_id = f"synthetic-live-{request_timestamp.strftime('%Y%m%dT%H%M%S')}-{index:06d}"

        return ExternalChargingRequest.model_validate(
            {
                "client_request_id": request_id,
                "request_timestamp": request_timestamp,
                "current_latitude": latitude,
                "current_longitude": longitude,
                "target_soc": target_soc,
                "current_soc": current_soc,
                "battery_kwh": profile.battery_kwh,
                "requested_energy_kwh": requested_energy_kwh,
                "preference_mode": preference_mode,
                "charger_type": charger_type,
                "latest_finish_ts": request_timestamp + timedelta(minutes=window_minutes),
                "source_type": "external_live",
                "request_id": request_id,
                "zone_id": station.zone_id,
                "vehicle_profile_id": profile.vehicle_profile_id,
                "vehicle_max_ac_kw": profile.ac_max_kw,
                "vehicle_max_dc_kw": profile.dc_max_kw,
                "metadata": {
                    "generator_type": "synthetic_live",
                    "generator_version": GENERATOR_VERSION,
                    "vehicle_profile_id": profile.vehicle_profile_id,
                    "anchor_station_id": station.station_id,
                    "anchor_zone_id": station.zone_id,
                    "synthetic_seed": self.seed,
                },
            }
        )

    def generate_batch(
        self,
        *,
        start_ts: datetime,
        end_ts: datetime,
        count: int,
    ) -> list[ExternalChargingRequest]:
        """Generate a deterministic batch within a timestamp window."""

        if count < 0:
            raise ValueError("count must be non-negative.")
        if end_ts < start_ts:
            raise ValueError("end_ts must be greater than or equal to start_ts.")
        slots = self._time_slots(start_ts, end_ts)
        requests: list[ExternalChargingRequest] = []
        for index in range(count):
            rng = self._rng("batch", start_ts.isoformat(), end_ts.isoformat(), count, index)
            timestamp = self._weighted_choice({slot: self._timestamp_weight(slot) for slot in slots}, rng)
            requests.append(self.generate_one(timestamp, index=index + 1))
        return requests

    def _choose_anchor_station(self, zone_id: str, rng: random.Random) -> _StationRecord:
        stations = [station for station in self.stations if station.zone_id == zone_id] or list(self.stations)
        weights = {
            station.station_id: max(station.sessions_total, 0.0) + max(float(station.cp_count_total), 1.0)
            for station in stations
        }
        station_id = self._weighted_choice(weights, rng)
        return next(station for station in stations if station.station_id == station_id)

    def _choose_vehicle_profile(self, rng: random.Random) -> VehicleProfile:
        profile_id = self._weighted_choice(
            {
                profile_id: max(float(profile.market_share), 0.0) or 1.0
                for profile_id, profile in self.vehicle_profiles.items()
            },
            rng,
        )
        return self.vehicle_profiles[str(profile_id)]

    def _choose_charger_type(
        self,
        preference_mode: str,
        station: _StationRecord,
        profile: VehicleProfile,
        rng: random.Random,
    ) -> str:
        connectors = self._connector_tokens(station.connector_mix_total)
        has_rapid = bool(connectors & {"rapid", "ultra_rapid", "ultrarapid", "dc"})
        if has_rapid and preference_mode == "fastest":
            return str(self._weighted_choice({"Rapid": 0.65, "Any": 0.25, "AC": 0.10}, rng))
        if has_rapid and profile.dc_max_kw >= 50.0:
            return str(self._weighted_choice({"Any": 0.50, "Rapid": 0.35, "AC": 0.15}, rng))
        return str(self._weighted_choice({"Any": 0.55, "AC": 0.45}, rng))

    def _jitter_location(self, station: _StationRecord, rng: random.Random) -> tuple[float, float]:
        # TODO: replace station jitter with sampled road-node origins when routing is introduced.
        distance_km = rng.uniform(0.2, 1.0)
        angle = rng.uniform(0.0, math.tau)
        latitude = station.latitude + (math.cos(angle) * distance_km / 111.0)
        longitude = station.longitude + (math.sin(angle) * distance_km / (111.0 * 0.56))
        return round(self._clamp(latitude, -90.0, 90.0), 6), round(self._clamp(longitude, -180.0, 180.0), 6)

    def _zone_weights(self) -> dict[str, float]:
        configured = (
            self.request_generator_params.get("zone_level_demand_share", {})
            .get("request_share", {})
        )
        if configured:
            return {str(zone_id): float(weight) for zone_id, weight in configured.items()}
        weights: dict[str, float] = {}
        for station in self.stations:
            weights[station.zone_id] = weights.get(station.zone_id, 0.0) + max(float(station.cp_count_total), 1.0)
        return weights

    def _preference_weights(self) -> dict[str, float]:
        configured = (
            self.request_generator_params.get("user_preference_mode", {})
            .get("realized_share", {})
        )
        weights = {str(key): float(value) for key, value in configured.items() if key in PREFERENCE_FALLBACK}
        return weights or dict(PREFERENCE_FALLBACK)

    def _timestamp_weight(self, timestamp: datetime) -> float:
        arrival = self.request_generator_params.get("arrival_distributions", {})
        hour_share = float(arrival.get("hour_share", {}).get(str(timestamp.hour), 1.0 / 24.0))
        month_share = float(arrival.get("month_share", {}).get(str(timestamp.month), 1.0 / 12.0))
        weekday_type = "weekend" if timestamp.weekday() >= 5 else "weekday"
        weekday_share = float(arrival.get("weekday_type_share", {}).get(weekday_type, 0.5))
        return max(hour_share * month_share * weekday_share, 0.000001)

    def _time_slots(self, start_ts: datetime, end_ts: datetime) -> list[datetime]:
        slots: list[datetime] = []
        current = start_ts
        while current <= end_ts:
            slots.append(current)
            current += timedelta(minutes=15)
        return slots or [start_ts]

    def _sample_summary(self, key: str, rng: random.Random, *, fallback: float) -> float:
        summary = self.request_generator_params.get(key, {})
        values = [
            float(summary[item])
            for item in ("p10", "p25", "median", "p75", "p90", "p95")
            if item in summary
        ]
        if not values:
            return fallback
        return float(values[min(int(rng.random() * len(values)), len(values) - 1)])

    def _rng(self, *parts: object) -> random.Random:
        seed_text = "|".join([self.seed, *(str(part) for part in parts)])
        digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
        return random.Random(int(digest[:16], 16))

    @staticmethod
    def _weighted_choice(weights: Mapping[Any, float], rng: random.Random) -> Any:
        items = [(key, max(float(value), 0.0)) for key, value in weights.items()]
        total = sum(value for _, value in items)
        if total <= 0.0:
            return items[0][0]
        bucket = rng.random() * total
        cumulative = 0.0
        for key, value in items:
            cumulative += value
            if bucket <= cumulative:
                return key
        return items[-1][0]

    @staticmethod
    def _connector_tokens(connector_mix_total: str) -> set[str]:
        return {item.strip().lower() for item in str(connector_mix_total).split(";") if item.strip()}

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @classmethod
    def _coerce_station(cls, station: Any) -> _StationRecord:
        return _StationRecord(
            station_id=str(cls._get(station, "station_id")),
            station_name=str(cls._get(station, "station_name", cls._get(station, "station_id"))),
            zone_id=str(cls._get(station, "zone_id")),
            latitude=float(cls._get(station, "latitude")),
            longitude=float(cls._get(station, "longitude")),
            cp_count_total=int(float(cls._get(station, "cp_count_total", 1) or 1)),
            connector_mix_total=str(cls._get(station, "connector_mix_total", "ac")),
            sessions_total=float(cls._get(station, "sessions_total", 0.0) or 0.0),
        )

    @staticmethod
    def _get(value: Any, key: str, default: Any = None) -> Any:
        if isinstance(value, Mapping):
            return value.get(key, default)
        return getattr(value, key, default)


__all__ = ["GENERATOR_VERSION", "SyntheticLiveRequestGenerator"]
