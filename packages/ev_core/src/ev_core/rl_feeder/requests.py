"""Composite request simulation for feeder-aligned EV RL."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta
from typing import Any, Sequence

import pandas as pd

from .contracts import FeederAction, FeederEpisodeScenario, FeederRequest


class FeederRequestGenerator:
    """Generate customer charging requests from exported behavioral priors."""

    def __init__(
        self,
        *,
        priors: pd.DataFrame | None = None,
        actions: Sequence[FeederAction],
        seed: int | str = "feeder-requests",
    ) -> None:
        self.priors = priors.copy() if priors is not None else pd.DataFrame()
        self.actions = list(actions)
        self.seed = str(seed)

    def generate_for_scenario(self, scenario: FeederEpisodeScenario) -> list[FeederRequest]:
        area_actions = [action for action in self.actions if action.secondary_area_id == scenario.secondary_area_id]
        if not area_actions:
            return []
        requests: list[FeederRequest] = []
        for index in range(max(int(scenario.request_count), 0)):
            requests.append(self._generate_one(scenario, area_actions=area_actions, index=index + 1))
        return requests

    def _generate_one(
        self,
        scenario: FeederEpisodeScenario,
        *,
        area_actions: list[FeederAction],
        index: int,
    ) -> FeederRequest:
        rng = self._rng(scenario.scenario_id, scenario.seed, index)
        prior = self._sample_prior(rng)
        duration_steps = int(_coalesce_number(prior, ["duration_steps"], 0.0))
        duration_minutes = int(
            duration_steps * 30
            if duration_steps > 0
            else _coalesce_number(prior, ["duration_minutes", "requested_duration_minutes"], 45.0)
        )
        slack_minutes = int(_coalesce_number(prior, ["slack_minutes"], 60.0))
        requested_energy = float(_coalesce_number(prior, ["requested_energy_kwh", "energy_kwh"], rng.uniform(12.0, 38.0)))
        battery_kwh = float(_coalesce_number(prior, ["battery_kwh"], rng.choice([50.0, 64.0, 75.0])))
        target_soc = _normalize_soc(float(_coalesce_number(prior, ["target_soc"], 0.8)))
        current_soc = _normalize_soc(
            float(_coalesce_number(prior, ["current_soc"], target_soc - requested_energy / max(battery_kwh, 1.0)))
        )
        current_soc = min(max(current_soc, 0.05), target_soc)
        slot_count = max(int((scenario.duration_hours * 60) / 15), 1)
        arrival = _coalesce_datetime(prior, ["arrival_timestamp"], None)
        if arrival is None:
            arrival = scenario.start_ts + timedelta(minutes=15 * rng.randrange(slot_count))
        anchor = area_actions[rng.randrange(len(area_actions))]
        charger_preference = str(prior.get("charger_type_preference") or prior.get("charger_type") or "any").lower()
        source = str(prior.get("source_system") or prior.get("source") or "synthetic_fallback")
        latest_finish = _coalesce_datetime(prior, ["latest_finish_timestamp"], None)
        if latest_finish is None or latest_finish <= arrival:
            latest_finish = arrival + timedelta(minutes=max(duration_minutes + slack_minutes, 30))
        metadata = _parse_metadata(prior.get("source_mix_metadata"))
        metadata.update(
            {
                "request_prior_sources": ",".join(scenario.request_prior_sources),
                "sampled_prior_source": source,
            }
        )
        return FeederRequest(
            request_id=f"feeder-req-{scenario.seed}-{index:06d}",
            secondary_area_id=scenario.secondary_area_id,
            arrival_timestamp=arrival,
            latest_finish_timestamp=latest_finish,
            requested_energy_kwh=round(requested_energy, 6),
            battery_kwh=round(battery_kwh, 6),
            current_soc=round(current_soc, 6),
            target_soc=round(target_soc, 6),
            charger_type_preference=charger_preference,
            max_ac_kw=float(_coalesce_number(prior, ["max_ac_kw", "vehicle_max_ac_kw"], min(anchor.charger_kw, 22.0))),
            max_dc_kw=float(_coalesce_number(prior, ["max_dc_kw", "vehicle_max_dc_kw"], max(anchor.charger_kw, 50.0))),
            origin_latitude=anchor.latitude,
            origin_longitude=anchor.longitude,
            origin_x=_optional_number(prior, ["origin_x"], anchor.x),
            origin_y=_optional_number(prior, ["origin_y"], anchor.y),
            source_mix_metadata=metadata,
        )

    def _sample_prior(self, rng: random.Random) -> dict[str, Any]:
        if self.priors.empty:
            return {}
        row = self.priors.iloc[rng.randrange(len(self.priors))]
        return row.to_dict()

    def _rng(self, *parts: object) -> random.Random:
        seed_text = "|".join([self.seed, *(str(part) for part in parts)])
        digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
        return random.Random(int(digest[:16], 16))


def _coalesce_number(row: dict[str, Any], columns: list[str], default: float) -> float:
    for column in columns:
        value = row.get(column)
        try:
            result = float(value)
        except (TypeError, ValueError):
            continue
        if result == result:
            return result
    return default


def _optional_number(row: dict[str, Any], columns: list[str], default: float | None) -> float | None:
    value = _coalesce_number(row, columns, float("nan"))
    if value == value:
        return value
    return default


def _normalize_soc(value: float) -> float:
    if value > 1.0:
        return max(min(value / 100.0, 1.0), 0.0)
    return max(min(value, 1.0), 0.0)


def _coalesce_datetime(row: dict[str, Any], columns: list[str], default: datetime | None) -> datetime | None:
    for column in columns:
        value = row.get(column)
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.lower() == "nan":
            continue
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is not None:
            return parsed.replace(tzinfo=None)
        return parsed
    return default


def _parse_metadata(value: Any) -> dict[str, str | float | int | bool | None]:
    if isinstance(value, dict):
        return {str(key): _metadata_value(item) for key, item in value.items()}
    if value is None:
        return {}
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"raw_source_mix_metadata": text}
    if not isinstance(parsed, dict):
        return {"raw_source_mix_metadata": text}
    return {str(key): _metadata_value(item) for key, item in parsed.items()}


def _metadata_value(value: Any) -> str | float | int | bool | None:
    if value is None or isinstance(value, (str, float, int, bool)):
        return value
    return str(value)


__all__ = ["FeederRequestGenerator"]
