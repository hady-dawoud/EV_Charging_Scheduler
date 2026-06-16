"""Pydantic models for the EV-side to grid-side advisory contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


GridVerdict = Literal["OK", "CAUTIOUS", "REJECT"]
GridRiskClass = Literal["SAFE", "NEAR", "VIOLATION"]
GridEvaluationMode = Literal["replay", "surrogate", "ac_pf", "opf", "hybrid", "mock"]
BottleneckElementType = Literal["none", "bus", "line", "transformer"]
PhysicalTruthLevel = Literal["unknown", "exact_candidate_pf", "node_pf", "area_pf", "opf_proxy", "adapter_proxy"]
LabelSourceKind = Literal[
    "unknown",
    "exact_candidate",
    "node_sensitivity",
    "area_reuse",
    "generated_pf_opf",
    "adapter_proxy",
    "unavailable",
]


class GridSchedulePoint(BaseModel):
    """One time step of proposed EV charging power."""

    model_config = ConfigDict(extra="forbid")

    time_index: int = Field(ge=0)
    p_kw: float = Field(ge=0.0)
    q_kvar: float = 0.0


class GridScheduleProposal(BaseModel):
    """Station/time/energy proposal sent from EV-side to DigitalTwin."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    episode_id: str | None = None
    station_id: str
    area_id: str
    secondary_area_id: str | None = None
    node_id: str | None = None
    demand_point_id: str | None = None
    asset_type: str | None = None
    source_system: str | None = None
    start_timestamp: datetime
    timebase_minutes: int = Field(default=30, ge=1)
    duration_steps: int = Field(default=1, ge=1)
    requested_energy_kwh: float = Field(ge=0.0)
    charger_kw: float = Field(ge=0.0)
    ev_schedule: list[GridSchedulePoint] = Field(default_factory=list)
    evaluation_mode: GridEvaluationMode = "replay"

    @field_validator("start_timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class BatchGridAdvisoryRequest(BaseModel):
    """Batch proposal request used by the RL environment for all candidates."""

    model_config = ConfigDict(extra="forbid")

    proposals: list[GridScheduleProposal]


class GridAdvisoryResponse(BaseModel):
    """Grid-side response consumed by observation and reward shaping."""

    model_config = ConfigDict(extra="forbid")

    verdict: GridVerdict = "OK"
    risk_class: GridRiskClass = "SAFE"
    v_min_pu: float = 1.0
    max_line_loading_percent: float = 0.0
    max_trafo_loading_percent: float = 0.0
    stress_score: float = 0.0
    baseline_v_min_pu: float = 1.0
    post_v_min_pu: float = 1.0
    delta_v_min_pu: float = 0.0
    baseline_max_line_loading_percent: float = 0.0
    post_max_line_loading_percent: float = 0.0
    delta_max_line_loading_percent: float = 0.0
    baseline_max_trafo_loading_percent: float = 0.0
    post_max_trafo_loading_percent: float = 0.0
    delta_max_trafo_loading_percent: float = 0.0
    voltage_violation_count: int = 0
    line_overload_count: int = 0
    trafo_overload_count: int = 0
    bottleneck_element_id: str | None = None
    bottleneck_element_type: BottleneckElementType = "none"
    bottleneck_margin_percent: float = 100.0
    max_allowed_kw: float = 0.0
    curtailment_required_kw: float = 0.0
    feasible_energy_kwh: float = 0.0
    opf_feasible: bool = True
    opf_objective_value: float = 0.0
    opf_curtailment_kwh: float = 0.0
    opf_cost_delta: float = 0.0
    losses_kw: float = 0.0
    delta_losses_kw: float = 0.0
    voltage_sensitivity_pu_per_kw: float = 0.0
    loading_sensitivity_percent_per_kw: float = 0.0
    ood_flag: bool = False
    uq_flag: bool = False
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    model_version: str = "disabled_grid_advisory"
    evaluation_mode_used: GridEvaluationMode = "mock"
    advisory_available: bool = True
    physical_truth_level: PhysicalTruthLevel = "unknown"
    label_source_kind: LabelSourceKind = "unknown"
    candidate_replay_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_snapshot_id: str | None = None
    source_scenario_id: str | None = None
    source_time_index: int | None = None
    source_campaign_id: str | None = None


class BatchGridAdvisoryResponse(BaseModel):
    """Batch response aligned one-to-one with request proposals."""

    model_config = ConfigDict(extra="forbid")

    responses: list[GridAdvisoryResponse]


class ConstraintEnvelopeRequest(BaseModel):
    """Ask DigitalTwin for a conservative station/area charging envelope."""

    model_config = ConfigDict(extra="forbid")

    area_id: str
    station_id: str | None = None
    start_timestamp: datetime | None = None
    timebase_minutes: int = Field(default=30, ge=1)
    horizon_steps: int = Field(default=1, ge=1)


class ConstraintEnvelopeResponse(BaseModel):
    """Simple envelope used for debugging and later runtime hard gating."""

    model_config = ConfigDict(extra="forbid")

    area_id: str
    station_id: str | None = None
    timebase_minutes: int
    max_allowed_kw: float
    model_version: str
    reason_codes: list[str] = Field(default_factory=list)


def neutral_grid_advisory_response(
    *,
    model_version: str = "disabled_grid_advisory",
    reason_codes: list[str] | None = None,
    advisory_available: bool = False,
) -> GridAdvisoryResponse:
    """Return a safe neutral response when grid advice is disabled or unavailable."""

    return GridAdvisoryResponse(
        verdict="OK",
        risk_class="SAFE",
        v_min_pu=1.0,
        max_line_loading_percent=0.0,
        max_trafo_loading_percent=0.0,
        stress_score=0.0,
        baseline_v_min_pu=1.0,
        post_v_min_pu=1.0,
        delta_v_min_pu=0.0,
        baseline_max_line_loading_percent=0.0,
        post_max_line_loading_percent=0.0,
        delta_max_line_loading_percent=0.0,
        baseline_max_trafo_loading_percent=0.0,
        post_max_trafo_loading_percent=0.0,
        delta_max_trafo_loading_percent=0.0,
        voltage_violation_count=0,
        line_overload_count=0,
        trafo_overload_count=0,
        bottleneck_element_id=None,
        bottleneck_element_type="none",
        bottleneck_margin_percent=100.0,
        max_allowed_kw=0.0,
        curtailment_required_kw=0.0,
        feasible_energy_kwh=0.0,
        opf_feasible=True,
        opf_objective_value=0.0,
        opf_curtailment_kwh=0.0,
        opf_cost_delta=0.0,
        losses_kw=0.0,
        delta_losses_kw=0.0,
        voltage_sensitivity_pu_per_kw=0.0,
        loading_sensitivity_percent_per_kw=0.0,
        ood_flag=False,
        uq_flag=False,
        confidence_score=1.0,
        reason_codes=reason_codes or ["grid_advisory_neutral"],
        model_version=model_version,
        evaluation_mode_used="mock",
        advisory_available=advisory_available,
        physical_truth_level="unknown",
        label_source_kind="unavailable" if not advisory_available else "unknown",
        candidate_replay_confidence=0.0,
    )


__all__ = [
    "BatchGridAdvisoryRequest",
    "BatchGridAdvisoryResponse",
    "ConstraintEnvelopeRequest",
    "ConstraintEnvelopeResponse",
    "GridAdvisoryResponse",
    "GridEvaluationMode",
    "LabelSourceKind",
    "PhysicalTruthLevel",
    "GridRiskClass",
    "GridSchedulePoint",
    "GridScheduleProposal",
    "GridVerdict",
    "neutral_grid_advisory_response",
]
