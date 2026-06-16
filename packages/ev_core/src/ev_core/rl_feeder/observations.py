"""Observation builder for feeder-aligned station-selection RL."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

import numpy as np

from ev_core.grid_advisory.contracts import GridAdvisoryResponse

from .contracts import FeederAction, FeederRequest


@dataclass(frozen=True)
class FeederObservationSpec:
    action_count: int
    global_feature_count: int
    action_feature_count: int
    vector_size: int


class FeederObservationBuilder:
    """Build a fixed flat vector over all feeder public-EV actions."""

    global_feature_count = 10
    action_feature_count = 30

    def __init__(self, *, actions: list[FeederAction], feature_stats: Mapping[str, Any] | None = None) -> None:
        self.actions = list(actions)
        self.feature_stats = dict(feature_stats or {})
        self.power_scale_kw = max(
            _stats_max(self.feature_stats, "actions", "charger_kw", 150.0),
            _stats_max(self.feature_stats, "actions", "public_ev_capacity_kw", 150.0),
            22.0,
        )
        self.energy_scale_kwh = max(_stats_max(self.feature_stats, "request_priors", "requested_energy_kwh", 80.0), 40.0)
        self.battery_scale_kwh = max(_stats_max(self.feature_stats, "request_priors", "battery_kwh", 100.0), 40.0)
        self.slack_scale_minutes = max(_stats_max(self.feature_stats, "request_priors", "slack_minutes", 240.0), 60.0)
        self.spec = FeederObservationSpec(
            action_count=len(self.actions),
            global_feature_count=self.global_feature_count,
            action_feature_count=self.action_feature_count,
            vector_size=self.global_feature_count + len(self.actions) * self.action_feature_count,
        )

    def zeros(self) -> np.ndarray:
        return np.zeros(self.spec.vector_size, dtype=np.float32)

    def build(
        self,
        *,
        request: FeederRequest | None,
        action_mask: list[bool],
        grid_advisories: Mapping[str, GridAdvisoryResponse] | None = None,
    ) -> np.ndarray:
        if request is None:
            return self.zeros()
        grid_advisories = grid_advisories or {}
        hour = request.arrival_timestamp.hour + request.arrival_timestamp.minute / 60.0
        angle = hour / 24.0 * math.tau
        slack_minutes = max((request.latest_finish_timestamp - request.arrival_timestamp).total_seconds() / 60.0, 0.0)
        values: list[float] = [
            math.sin(angle),
            math.cos(angle),
            _clip01(float(request.requested_energy_kwh) / self.energy_scale_kwh),
            _clip01(float(slack_minutes) / self.slack_scale_minutes),
            _clip01(float(request.battery_kwh) / self.battery_scale_kwh),
            _clip01(float(request.current_soc)),
            _clip01(float(request.target_soc)),
            _clip01(float(request.max_ac_kw) / max(self.power_scale_kw, 1.0)),
            _clip01(float(request.max_dc_kw) / max(self.power_scale_kw, 1.0)),
            1.0,
        ]
        for index, action in enumerate(self.actions):
            advisory = grid_advisories.get(action.station_id)
            connector_type = _canonical_connector_type(action.connector_type)
            values.extend(
                [
                    1.0 if action.secondary_area_id == request.secondary_area_id else 0.0,
                    1.0 if bool(action_mask[index]) else 0.0,
                    _clip01(_as_float(action.p_base_kw) / max(self.power_scale_kw, 1.0)),
                    _clip01(_as_float(action.public_ev_capacity_kw) / max(self.power_scale_kw, 1.0)),
                    _clip01(_as_float(action.charger_kw) / max(self.power_scale_kw, 1.0)),
                    1.0 if connector_type in {"ac", "any"} else 0.0,
                    1.0 if connector_type in {"dc", "rapid", "ultra_rapid", "any"} else 0.0,
                    *self._grid_features(advisory),
                ]
            )
        return np.asarray(values, dtype=np.float32)

    def _grid_features(self, advisory: GridAdvisoryResponse | None) -> list[float]:
        if advisory is None:
            return [0.0] * 23
        return [
            1.0 if advisory.advisory_available else 0.0,
            _verdict_code(advisory.verdict),
            _risk_code(advisory.risk_class),
            _as_float(advisory.candidate_replay_confidence),
            _physical_truth_code(advisory.physical_truth_level),
            _label_source_code(advisory.label_source_kind),
            _as_float(advisory.stress_score),
            _as_float(advisory.post_v_min_pu),
            _as_float(advisory.delta_v_min_pu),
            _as_float(advisory.post_max_line_loading_percent) / 100.0,
            _as_float(advisory.delta_max_line_loading_percent) / 100.0,
            _as_float(advisory.post_max_trafo_loading_percent) / 100.0,
            _as_float(advisory.delta_max_trafo_loading_percent) / 100.0,
            _as_float(advisory.voltage_violation_count),
            _as_float(advisory.line_overload_count),
            _as_float(advisory.trafo_overload_count),
            _as_float(advisory.bottleneck_margin_percent) / 100.0,
            _as_float(advisory.max_allowed_kw) / max(self.power_scale_kw, 1.0),
            _as_float(advisory.curtailment_required_kw) / max(self.power_scale_kw, 1.0),
            1.0 if advisory.opf_feasible else 0.0,
            _as_float(advisory.opf_curtailment_kwh) / 100.0,
            1.0 if advisory.ood_flag else 0.0,
            1.0 if advisory.uq_flag else 0.0,
        ]


def _verdict_code(value: str) -> float:
    if str(value).upper() == "REJECT":
        return -1.0
    if str(value).upper() == "CAUTIOUS":
        return 0.0
    return 1.0


def _risk_code(value: str) -> float:
    if str(value).upper() == "VIOLATION":
        return 1.0
    if str(value).upper() == "NEAR":
        return 0.5
    return 0.0


def _physical_truth_code(value: str) -> float:
    normalized = str(value).strip().lower()
    return {
        "exact_candidate_pf": 1.0,
        "node_pf": 0.8,
        "area_pf": 0.55,
        "opf_proxy": 0.45,
        "adapter_proxy": -0.5,
    }.get(normalized, 0.0)


def _label_source_code(value: str) -> float:
    normalized = str(value).strip().lower()
    return {
        "exact_candidate": 1.0,
        "node_sensitivity": 0.75,
        "area_reuse": 0.45,
        "generated_pf_opf": 0.9,
        "adapter_proxy": -0.5,
        "unavailable": -1.0,
    }.get(normalized, 0.0)


def _as_float(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if not math.isfinite(result) else result


def _clip01(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return min(max(value, 0.0), 1.0)


def _canonical_connector_type(value: object) -> str:
    normalized = str(value or "any").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"", "any"}:
        return "any"
    if normalized in {"ac", "type_2", "type2"}:
        return "ac"
    if normalized in {"dc", "dc_fast", "ccs", "ccs2", "chademo", "tesla_supercharger"}:
        return "dc"
    if normalized in {"rapid", "fast", "rapid_dc"}:
        return "rapid"
    if normalized in {"ultrarapid", "ultra_rapid", "ultra_rapid_dc"}:
        return "ultra_rapid"
    return normalized


def _stats_max(stats: Mapping[str, Any], group: str, column: str, default: float) -> float:
    try:
        value = stats[group][column]["max"]
    except (KeyError, TypeError):
        return float(default)
    return max(_as_float(value), float(default))


__all__ = ["FeederObservationBuilder", "FeederObservationSpec"]
