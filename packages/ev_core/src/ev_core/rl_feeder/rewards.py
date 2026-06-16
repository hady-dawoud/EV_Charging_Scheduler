"""Reward model for feeder-aligned public-EV station selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

from ev_core.grid_advisory.contracts import GridAdvisoryResponse

from .contracts import FeederAction, FeederRequest


@dataclass(frozen=True)
class FeederRewardBreakdown:
    served_reward: float = 0.0
    invalid_action_penalty: float = 0.0
    missed_request_penalty: float = 0.0
    capacity_penalty: float = 0.0
    distance_penalty: float = 0.0
    wait_penalty: float = 0.0
    tariff_penalty: float = 0.0
    duration_penalty: float = 0.0
    stress_penalty: float = 0.0
    voltage_delta_penalty: float = 0.0
    loading_delta_penalty: float = 0.0
    violation_penalty: float = 0.0
    opf_penalty: float = 0.0
    curtailment_penalty: float = 0.0
    uncertainty_penalty: float = 0.0

    @property
    def total(self) -> float:
        return sum(asdict(self).values())

    def to_dict(self) -> dict[str, float]:
        payload = asdict(self)
        payload["total"] = self.total
        return payload


class FeederStationSelectionReward:
    """Compose user-service and grid-impact terms into one scalar reward."""

    def compute(
        self,
        *,
        selected_action: FeederAction | None = None,
        request: FeederRequest | None = None,
        grid_advisory: GridAdvisoryResponse | None = None,
        invalid_action: bool = False,
        missed: bool = False,
    ) -> FeederRewardBreakdown:
        if invalid_action:
            return FeederRewardBreakdown(invalid_action_penalty=-2.0)
        if missed:
            return FeederRewardBreakdown(missed_request_penalty=-1.5)
        if selected_action is None or request is None:
            return FeederRewardBreakdown(missed_request_penalty=-1.5)

        capacity_penalty = self._capacity_penalty(selected_action, request)
        distance_penalty = self._distance_penalty(selected_action, request)
        grid_terms = self._grid_terms(grid_advisory)
        return FeederRewardBreakdown(
            served_reward=1.0,
            capacity_penalty=capacity_penalty,
            distance_penalty=distance_penalty,
            **grid_terms,
        )

    def _capacity_penalty(self, action: FeederAction, request: FeederRequest) -> float:
        requested_kw = request.max_dc_kw if _prefers_dc(request) else request.max_ac_kw
        available_kw = max(min(action.public_ev_capacity_kw, action.charger_kw), 0.0)
        if requested_kw <= 0.0 or available_kw >= requested_kw:
            return 0.0
        return -min((requested_kw - available_kw) / max(requested_kw, 1.0), 1.0) * 0.35

    def _distance_penalty(self, action: FeederAction, request: FeederRequest) -> float:
        if action.x is not None and action.y is not None and request.origin_x is not None and request.origin_y is not None:
            distance = math.hypot(float(action.x) - float(request.origin_x), float(action.y) - float(request.origin_y))
            return -min(distance / 5000.0, 1.0) * 0.15
        if (
            action.latitude is not None
            and action.longitude is not None
            and request.origin_latitude is not None
            and request.origin_longitude is not None
        ):
            distance_degrees = math.hypot(
                float(action.latitude) - float(request.origin_latitude),
                float(action.longitude) - float(request.origin_longitude),
            )
            return -min(distance_degrees / 0.05, 1.0) * 0.15
        return 0.0

    def _grid_terms(self, advisory: GridAdvisoryResponse | None) -> dict[str, float]:
        if advisory is None or not advisory.advisory_available:
            return {
                "stress_penalty": 0.0,
                "voltage_delta_penalty": 0.0,
                "loading_delta_penalty": 0.0,
                "violation_penalty": 0.0,
                "opf_penalty": 0.0,
                "curtailment_penalty": 0.0,
                "uncertainty_penalty": -0.15 if advisory is not None else 0.0,
            }

        stress = _as_float(advisory.stress_score)
        voltage_drop = max(-_as_float(advisory.delta_v_min_pu), 0.0)
        line_delta = max(_as_float(advisory.delta_max_line_loading_percent), 0.0)
        trafo_delta = max(_as_float(advisory.delta_max_trafo_loading_percent), 0.0)
        violation_count = (
            _as_float(advisory.voltage_violation_count)
            + _as_float(advisory.line_overload_count)
            + _as_float(advisory.trafo_overload_count)
        )
        curtailment = max(_as_float(advisory.opf_curtailment_kwh), _as_float(advisory.curtailment_required_kw))
        uncertainty_flags = int(bool(advisory.ood_flag)) + int(bool(advisory.uq_flag))
        provenance_penalty = _truth_level_penalty(advisory.physical_truth_level)

        return {
            "stress_penalty": -min(stress * 0.65, 1.0),
            "voltage_delta_penalty": -min(voltage_drop * 12.0, 1.0),
            "loading_delta_penalty": -min((line_delta + trafo_delta) / 120.0, 1.0),
            "violation_penalty": -min(violation_count * 0.8, 2.4),
            "opf_penalty": -1.0 if not advisory.opf_feasible else 0.0,
            "curtailment_penalty": -min(curtailment / 40.0, 1.0),
            "uncertainty_penalty": -0.2 * uncertainty_flags + provenance_penalty,
        }


def _prefers_dc(request: FeederRequest) -> bool:
    return str(request.charger_type_preference).strip().lower() in {"dc", "rapid", "ultra_rapid"}


def _as_float(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if not math.isfinite(result) else result


def _truth_level_penalty(value: object) -> float:
    normalized = str(value).strip().lower()
    if normalized in {"exact_candidate_pf", "node_pf"}:
        return 0.0
    if normalized == "area_pf":
        return -0.05
    if normalized == "opf_proxy":
        return -0.08
    if normalized == "adapter_proxy":
        return -0.35
    return -0.1


__all__ = ["FeederRewardBreakdown", "FeederStationSelectionReward"]
