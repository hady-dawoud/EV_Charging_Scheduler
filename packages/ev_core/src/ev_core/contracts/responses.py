"""Standalone response and snapshot contracts for the EV-side runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecommendationOption(BaseModel):
    """Single ranked charging recommendation candidate."""

    model_config = ConfigDict(extra="forbid")

    station_id: str
    station_name: str
    zone_id: str
    transformer_id: str
    score: float
    distance_km: float
    estimated_wait_minutes: int
    estimated_duration_minutes: int
    estimated_cost_gbp: float
    transformer_headroom_kw: float
    current_queue: int
    utilization: float
    charger_compatible: bool
    reason_tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    """Recommendation bundle returned for a runtime request."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    client_request_id: Optional[str] = None
    simulated_timestamp: datetime
    zone_id: Optional[str] = None
    top_recommendation: Optional[RecommendationOption] = None
    alternatives: List[RecommendationOption] = Field(default_factory=list)
    congestion_note: Optional[str] = None
    debug_reasoning_summary: str = ""
    source_type: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RequestSnapshot(BaseModel):
    """Live request/session state exposed through runtime snapshots."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    client_request_id: Optional[str] = None
    source_type: str
    status: str
    arrival_ts: datetime
    latest_finish_ts: datetime
    requested_energy_kwh: float
    requested_duration_minutes: int
    preference_mode: str
    charger_type_preference: str
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    transformer_id: Optional[str] = None
    zone_id: Optional[str] = None
    queue_entered_ts: Optional[datetime] = None
    started_at: Optional[datetime] = None
    expected_completion_ts: Optional[datetime] = None
    remaining_minutes: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StationStateSnapshot(BaseModel):
    """Station-level operational snapshot for the dashboard and runtime API."""

    model_config = ConfigDict(extra="forbid")

    station_id: str
    station_name: str
    zone_id: str
    transformer_id: str
    latitude: float
    longitude: float
    cp_count_total: int
    station_capacity_kw_assumed: float
    active_sessions: int
    queue_length: int
    utilization: float
    estimated_wait_minutes: int
    transformer_headroom_kw: float
    active_request_ids: List[str] = Field(default_factory=list)
    queued_request_ids: List[str] = Field(default_factory=list)


class TransformerStateSnapshot(BaseModel):
    """Transformer-level operational snapshot on the shared 15-minute time base."""

    model_config = ConfigDict(extra="forbid")

    transformer_id: str
    transformer_name: str
    zone_id: str
    capacity_kw: float
    background_load_kw: float
    ev_load_kw: float
    pv_generation_kw: float
    net_load_kw: float
    headroom_kw: float
    overload: bool
    attached_station_ids: List[str] = Field(default_factory=list)


class MetricsSnapshot(BaseModel):
    """Compact runtime metrics used by the dashboard and demo tooling."""

    model_config = ConfigDict(extra="forbid")

    simulated_timestamp: datetime
    active_policy: str
    active_request_count: int
    queued_request_count: int
    active_session_count: int
    completed_requests_total: int
    missed_requests_total: int
    overload_event_count: int
    queue_length_total: int
    requests_seen_total: int
    queue_length_by_zone: Dict[str, int] = Field(default_factory=dict)
    requests_by_zone: Dict[str, int] = Field(default_factory=dict)
    transformer_loading_kw: Dict[str, float] = Field(default_factory=dict)
    transformer_headroom_kw: Dict[str, float] = Field(default_factory=dict)


class StateSnapshot(BaseModel):
    """Serializable runtime state snapshot for resume, storage, and dashboards."""

    model_config = ConfigDict(extra="forbid")

    simulated_timestamp: datetime
    active_policy: str
    replay_year: int
    replay_day: str
    runtime_mode: str = "replay"
    demand_multiplier: float = 1.0
    warm_start_minutes: int = 0
    loop_running: bool = False
    loop_interval_seconds: float = 0.0
    operational_start_ts: Optional[datetime] = None
    running: bool
    replay_cursor: int
    replay_total: int
    next_replay_arrival_ts: Optional[datetime] = None
    latest_external_request_id: Optional[str] = None
    active_requests: List[RequestSnapshot] = Field(default_factory=list)
    queued_requests: List[RequestSnapshot] = Field(default_factory=list)
    active_sessions: List[RequestSnapshot] = Field(default_factory=list)
    recently_completed_request_ids: List[str] = Field(default_factory=list)
    recently_missed_request_ids: List[str] = Field(default_factory=list)
    stations: List[StationStateSnapshot] = Field(default_factory=list)
    transformers: List[TransformerStateSnapshot] = Field(default_factory=list)
    metrics: MetricsSnapshot
    metadata: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "MetricsSnapshot",
    "RecommendationOption",
    "RecommendationResponse",
    "RequestSnapshot",
    "StateSnapshot",
    "StationStateSnapshot",
    "TransformerStateSnapshot",
]
