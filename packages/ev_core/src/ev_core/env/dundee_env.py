"""Dundee-specific request-driven charging environment."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Mapping
from uuid import uuid4

from ev_core.contracts.events import RuntimeEvent
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import (
    MetricsSnapshot,
    RecommendationResponse,
    RequestSnapshot,
    StateSnapshot,
    StationStateSnapshot,
    TransformerStateSnapshot,
)
from ev_core.config.recommendation import is_rl_safety_policy
from ev_core.data.repositories import DundeeDataBundle
from ev_core.forecasting.provider import ForecastProvider, ForecastRequest, NullForecastProvider
from ev_core.pricing.dundee_tariffs import build_dundee_tariff_metadata
from ev_core.pricing.dynamic_pricing import DynamicPricingInput, DynamicPricingResult, calculate_dynamic_price
from ev_core.recommender.candidates import CandidateBuilder
from ev_core.recommender.eligibility import StationEligibilityFilter
from ev_core.recommender.feeder_runtime_context import FEEDER_POLICY_NAME, build_feeder_runtime_context
from ev_core.recommender.ranker import CandidateContext
from ev_core.recommender.service import RecommendationService
from ev_core.routing.providers import RouteEstimate, RoutingProvider
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider, simple_distance_km
from ev_core.topology.scenarios import TopologyScenario, TopologyScenarioProvider
from ev_core.utils.timebase import (
    TIME_STEP_MINUTES,
    advance_timebase,
    ceil_to_timebase,
    floor_to_timebase,
    minutes_between,
)
from ev_core.vehicles.duration import estimate_connector_effective_power_kw, estimate_effective_power_kw

from .allocator import AllocationDecision
from .baselines import get_policy
from .entities import (
    ActiveChargingSession,
    ChargingConnector,
    GridContext,
    SimulationRequest,
    Station,
    StationRuntimeState,
    Transformer,
)
from .environment import SimulationEnvironment, StepResult
from .reward import RewardBreakdown


RL_SAFETY_RUNTIME_CONTEXT_KEYS = (
    "rl_safety_filter_enabled",
    "rl_safety_filter_mode",
    "rl_safety_filter_strict",
    "rl_safety_filter_penalty_weight",
    "rl_safety_block_unsafe",
    "rl_safety_mapping_mode",
)


def policy_requires_feeder_context(
    policy_name: str | None,
    metadata: Mapping[str, Any] | None = None,
) -> bool:
    return bool(
        policy_name == FEEDER_POLICY_NAME
        or is_rl_safety_policy(policy_name)
        or (metadata or {}).get("rl_safety_filter_enabled")
    )


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value != value:
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


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


class DundeeEnv(SimulationEnvironment):
    """Runnable Dundee simulator environment built from processed replay inputs."""

    def __init__(
        self,
        bundle: DundeeDataBundle,
        *,
        policy_mode: str = "overload_aware",
        replay_year: int = 2024,
        start_time: datetime | None = None,
        runtime_mode: str = "replay",
        demand_multiplier: float = 1.0,
        operational_start_time: datetime | None = None,
        warm_start_minutes: int = 0,
        replay_window_start: datetime | None = None,
        replay_window_end: datetime | None = None,
        forecast_provider: ForecastProvider | None = None,
        topology_scenario: TopologyScenario | None = None,
        topology_provider: TopologyScenarioProvider | None = None,
        dynamic_pricing_enabled: bool = True,
        routing_provider: RoutingProvider | None = None,
    ) -> None:
        self.bundle = bundle
        self.topology_provider = topology_provider or TopologyScenarioProvider(topology_scenario)
        self.topology_scenario = self.topology_provider.scenario
        self.topology_station_rows = self.topology_provider.apply_to_station_rows(bundle.stations)
        self.topology_transformer_rows = self.topology_provider.transformer_rows(
            bundle.transformers,
            station_rows=self.topology_station_rows,
        )
        self.request_generator_params = bundle.request_generator_params
        self.candidate_builder = CandidateBuilder()
        self.station_eligibility_filter = StationEligibilityFilter()
        self.recommendation_service = RecommendationService()
        self.forecast_provider = forecast_provider or NullForecastProvider()
        self.dynamic_pricing_enabled = bool(dynamic_pricing_enabled)
        self.routing_provider = routing_provider or SimpleDistanceRoutingProvider()
        self.last_routing_fallback_reason: str | None = None
        self._route_estimate_cache: dict[tuple[str, str], RouteEstimate] = {}
        self.policy_mode = policy_mode
        self.replay_year = replay_year
        self.runtime_mode = runtime_mode
        self.demand_multiplier = max(float(demand_multiplier), 0.0)
        self.warm_start_minutes = max(int(warm_start_minutes), 0)
        self.station_index = self._build_station_index(bundle)
        self.transformer_index = self._build_transformer_index(bundle)
        self.stations_runtime: dict[str, StationRuntimeState] = {
            station_id: StationRuntimeState(station=station)
            for station_id, station in self.station_index.items()
        }
        self.replay_requests = self._select_replay_table(replay_year)
        initial_time = start_time or self.replay_requests["arrival_slot"].min().to_pydatetime()
        self.operational_start_time = floor_to_timebase(operational_start_time or initial_time)
        self.replay_window_start = floor_to_timebase(replay_window_start or initial_time)
        self.replay_window_end = floor_to_timebase(
            replay_window_end or datetime.combine(self.operational_start_time.date(), time(hour=23, minute=45))
        )
        if self.replay_window_end < self.operational_start_time:
            self.replay_window_end = self.operational_start_time
        self.current_time = self.replay_window_start
        self.replay_day = self.operational_start_time.date()
        self.replay_day_frame = self._slice_replay_window(self.replay_window_start, self.replay_window_end)
        self.running = False
        self.replay_cursor = 0
        self.synthetic_request_sequence = 0
        self.requests: dict[str, SimulationRequest] = {}
        self.active_sessions: dict[str, ActiveChargingSession] = {}
        self.recent_events: list[RuntimeEvent] = []
        self.recently_completed_request_ids: list[str] = []
        self.recently_missed_request_ids: list[str] = []
        self.completed_requests_total = 0
        self.missed_requests_total = 0
        self.requests_seen_total = 0
        self.overload_event_count = 0
        self.latest_external_request_id: str | None = None
        super().__init__(stations=list(self.station_index.values()), resolution_minutes=TIME_STEP_MINUTES)
        self.reset(
            start_time=self.replay_window_start,
            replay_day=self.replay_day,
            policy_mode=policy_mode,
            runtime_mode=runtime_mode,
            demand_multiplier=self.demand_multiplier,
            operational_start_time=self.operational_start_time,
            warm_start_minutes=self.warm_start_minutes,
            replay_window_start=self.replay_window_start,
            replay_window_end=self.replay_window_end,
        )

    @classmethod
    def from_state_snapshot(
        cls,
        bundle: DundeeDataBundle,
        snapshot: StateSnapshot,
        *,
        forecast_provider: ForecastProvider | None = None,
        topology_scenario: TopologyScenario | None = None,
        routing_provider: RoutingProvider | None = None,
    ) -> "DundeeEnv":
        """Restore a Dundee environment from a serialized state snapshot."""

        env = cls(
            bundle,
            policy_mode=snapshot.active_policy,
            replay_year=snapshot.replay_year,
            start_time=snapshot.simulated_timestamp,
            runtime_mode=snapshot.runtime_mode,
            demand_multiplier=snapshot.demand_multiplier,
            operational_start_time=snapshot.operational_start_ts,
            warm_start_minutes=snapshot.warm_start_minutes,
            replay_window_start=(
                datetime.fromisoformat(str(snapshot.metadata.get("replay_window_start")))
                if snapshot.metadata.get("replay_window_start")
                else snapshot.simulated_timestamp
            ),
            replay_window_end=(
                datetime.fromisoformat(str(snapshot.metadata.get("replay_window_end")))
                if snapshot.metadata.get("replay_window_end")
                else datetime.combine(date.fromisoformat(snapshot.replay_day), time(hour=23, minute=45))
            ),
            forecast_provider=forecast_provider,
            topology_scenario=topology_scenario,
            dynamic_pricing_enabled=bool(snapshot.metadata.get("dynamic_pricing_enabled", True)),
            routing_provider=routing_provider,
        )
        env.restore(snapshot)
        return env

    def reset(
        self,
        *,
        start_time: datetime | None = None,
        replay_day: date | None = None,
        policy_mode: str | None = None,
        runtime_mode: str | None = None,
        demand_multiplier: float | None = None,
        operational_start_time: datetime | None = None,
        warm_start_minutes: int | None = None,
        replay_window_start: datetime | None = None,
        replay_window_end: datetime | None = None,
    ) -> dict[str, Any]:
        """Reset the Dundee environment to the chosen replay day and policy."""

        if policy_mode is not None:
            self.policy_mode = policy_mode
        if runtime_mode is not None:
            self.runtime_mode = runtime_mode
        if demand_multiplier is not None:
            self.demand_multiplier = max(float(demand_multiplier), 0.0)
        if warm_start_minutes is not None:
            self.warm_start_minutes = max(int(warm_start_minutes), 0)
        base_time = start_time or operational_start_time or self.current_time
        if replay_day is None:
            replay_day = base_time.date()
        if operational_start_time is None:
            operational_start_time = base_time
        self.operational_start_time = floor_to_timebase(operational_start_time)
        if replay_window_start is None:
            replay_window_start = start_time or self.operational_start_time
        if replay_window_end is None:
            replay_window_end = datetime.combine(self.operational_start_time.date(), time(hour=23, minute=45))
        self.replay_window_start = floor_to_timebase(replay_window_start)
        self.replay_window_end = floor_to_timebase(replay_window_end)
        if self.replay_window_end < self.operational_start_time:
            self.replay_window_end = self.operational_start_time
        self.current_time = floor_to_timebase(start_time or self.replay_window_start)
        self.replay_day = replay_day
        self.replay_day_frame = self._slice_replay_window(self.replay_window_start, self.replay_window_end)
        self.replay_cursor = 0
        self.running = False
        self.synthetic_request_sequence = 0
        self.requests = {}
        self.active_sessions = {}
        for station_state in self.stations_runtime.values():
            station_state.active_session_ids.clear()
            station_state.queue_request_ids.clear()
        self.recent_events = []
        self.recently_completed_request_ids = []
        self.recently_missed_request_ids = []
        self.completed_requests_total = 0
        self.missed_requests_total = 0
        self.requests_seen_total = 0
        self.overload_event_count = 0
        self.latest_external_request_id = None
        self.last_routing_fallback_reason = None
        self._route_estimate_cache = {}
        self._record_event(
            "reset",
            summary="Environment reset for the selected Dundee runtime window.",
            payload={
                "policy_mode": self.policy_mode,
                "replay_day": replay_day.isoformat(),
                "runtime_mode": self.runtime_mode,
                "demand_multiplier": self.demand_multiplier,
                "warm_start_minutes": self.warm_start_minutes,
            },
        )
        return self.get_state_snapshot().model_dump(mode="json")

    def restore(self, snapshot: StateSnapshot) -> None:
        """Restore mutable Dundee runtime state from a snapshot."""

        self.current_time = snapshot.simulated_timestamp
        self.policy_mode = snapshot.active_policy
        self.replay_year = snapshot.replay_year
        self.replay_day = date.fromisoformat(snapshot.replay_day)
        self.runtime_mode = snapshot.runtime_mode
        self.demand_multiplier = snapshot.demand_multiplier
        self.warm_start_minutes = snapshot.warm_start_minutes
        self.operational_start_time = snapshot.operational_start_ts or snapshot.simulated_timestamp
        self.replay_window_start = (
            datetime.fromisoformat(str(snapshot.metadata.get("replay_window_start")))
            if snapshot.metadata.get("replay_window_start")
            else snapshot.simulated_timestamp
        )
        self.replay_window_end = (
            datetime.fromisoformat(str(snapshot.metadata.get("replay_window_end")))
            if snapshot.metadata.get("replay_window_end")
            else datetime.combine(self.replay_day, time(hour=23, minute=45))
        )
        self.replay_day_frame = self._slice_replay_window(self.replay_window_start, self.replay_window_end)
        self.replay_cursor = snapshot.replay_cursor
        self.running = snapshot.running
        self.latest_external_request_id = snapshot.latest_external_request_id
        self.synthetic_request_sequence = int(snapshot.metadata.get("synthetic_request_sequence", 0))
        self.completed_requests_total = snapshot.metrics.completed_requests_total
        self.missed_requests_total = snapshot.metrics.missed_requests_total
        self.requests_seen_total = snapshot.metrics.requests_seen_total
        self.overload_event_count = snapshot.metrics.overload_event_count
        self.recently_completed_request_ids = list(snapshot.recently_completed_request_ids)
        self.recently_missed_request_ids = list(snapshot.recently_missed_request_ids)
        self.last_routing_fallback_reason = snapshot.metadata.get("last_routing_fallback_reason")
        self._route_estimate_cache = {}
        self.requests = {}
        self.active_sessions = {}
        for station_state in self.stations_runtime.values():
            station_state.active_session_ids.clear()
            station_state.queue_request_ids.clear()
        snapshots = [*snapshot.active_requests, *snapshot.queued_requests, *snapshot.active_sessions]
        for request_snapshot in snapshots:
            request = SimulationRequest(
                request_id=request_snapshot.request_id,
                client_request_id=request_snapshot.client_request_id,
                source_type=request_snapshot.source_type,
                arrival_ts=request_snapshot.arrival_ts,
                latest_finish_ts=request_snapshot.latest_finish_ts,
                requested_energy_kwh=request_snapshot.requested_energy_kwh,
                requested_duration_minutes=request_snapshot.requested_duration_minutes,
                preference_mode=request_snapshot.preference_mode,
                charger_type_preference=request_snapshot.charger_type_preference,
                zone_id=request_snapshot.zone_id,
                assigned_station_id=request_snapshot.station_id,
                assigned_transformer_id=request_snapshot.transformer_id,
                status=request_snapshot.status,
                queue_entered_ts=request_snapshot.queue_entered_ts,
                started_at=request_snapshot.started_at,
                expected_completion_ts=request_snapshot.expected_completion_ts,
                remaining_minutes=request_snapshot.remaining_minutes,
                metadata=request_snapshot.metadata,
            )
            self.requests[request.request_id] = request
            if request.status == "queued" and request.assigned_station_id:
                self.stations_runtime[request.assigned_station_id].queue_request_ids.append(request.request_id)
            if request.status == "charging" and request.assigned_station_id and request.assigned_transformer_id and request.started_at and request.expected_completion_ts:
                self.stations_runtime[request.assigned_station_id].active_session_ids.append(request.request_id)
                self.active_sessions[request.request_id] = ActiveChargingSession(
                    request_id=request.request_id,
                    station_id=request.assigned_station_id,
                    transformer_id=request.assigned_transformer_id,
                    started_at=request.started_at,
                    expected_completion_ts=request.expected_completion_ts,
                    assigned_power_kw=max(
                        request.requested_energy_kwh * 60.0 / max(request.requested_duration_minutes, TIME_STEP_MINUTES),
                        1.0,
                    ),
                    estimated_cost_gbp=0.0,
                )

    def start(self) -> StateSnapshot:
        """Mark the environment as running and return the current snapshot."""

        self.running = True
        self._record_event("runtime_started", summary="Simulation runtime started.")
        return self.get_state_snapshot()

    def pause(self) -> StateSnapshot:
        """Pause the environment while preserving its current state."""

        self.running = False
        self._record_event("runtime_paused", summary="Simulation runtime paused.")
        return self.get_state_snapshot()

    def inject_external_request(self, request: ExternalChargingRequest) -> SimulationRequest:
        """Inject a live-style request into the local Dundee runtime."""

        simulation_request = self._build_simulation_request_from_external(request)
        self.requests[simulation_request.request_id] = simulation_request
        self.requests_seen_total += 1
        self.latest_external_request_id = simulation_request.request_id
        self._record_event(
            "external_request_injected",
            request_id=simulation_request.request_id,
            zone_id=simulation_request.zone_id,
            source_type=simulation_request.source_type,
            summary="External live-style request injected into the runtime.",
            payload={"client_request_id": request.client_request_id},
        )
        return simulation_request

    def get_ranked_recommendations(
        self,
        request: SimulationRequest | ExternalChargingRequest,
        recommendation_policy_name: str | None = None,
        policy_selection_metadata: dict | None = None,
    ) -> RecommendationResponse:
        """Rank Dundee stations for the provided request against the current state."""

        simulation_request = request if isinstance(request, SimulationRequest) else self._build_simulation_request_from_external(request)
        contexts = self._build_candidate_contexts(simulation_request)
        runtime_context = {"simulated_timestamp": self.current_time}
        response_metadata = dict(policy_selection_metadata or {})
        runtime_context.update(
            {
                key: response_metadata[key]
                for key in RL_SAFETY_RUNTIME_CONTEXT_KEYS
                if key in response_metadata
            }
        )
        forecast_metadata = {
            str(key): value
            for key, value in response_metadata.items()
            if str(key).startswith("forecast_")
        }
        if forecast_metadata:
            runtime_context["forecast_metadata"] = forecast_metadata
        if policy_requires_feeder_context(
            recommendation_policy_name,
            response_metadata,
        ):
            feeder_context = build_feeder_runtime_context(
                simulation_request,
                feeder_rl_data_dir=response_metadata.get("feeder_data_dir"),
            )
            runtime_context.update(feeder_context.runtime_context)
            runtime_context.update(feeder_context.metadata)
            response_metadata.update(feeder_context.metadata)
        response = self.recommendation_service.recommend(
            request_id=simulation_request.request_id,
            client_request_id=simulation_request.client_request_id,
            simulated_timestamp=self.current_time,
            zone_id=simulation_request.zone_id,
            source_type=simulation_request.source_type,
            preference_mode=simulation_request.preference_mode,
            candidate_contexts=contexts,
            policy_name=recommendation_policy_name,
            policy_selection_metadata=response_metadata,
            runtime_context=runtime_context,
        )
        top_station = response.top_recommendation.station_id if response.top_recommendation is not None else None
        top_transformer = response.top_recommendation.transformer_id if response.top_recommendation is not None else None
        self._record_event(
            "recommendation_generated",
            request_id=simulation_request.request_id,
            station_id=top_station,
            transformer_id=top_transformer,
            zone_id=simulation_request.zone_id,
            source_type=simulation_request.source_type,
            summary=(
                f"Generated {1 + len(response.alternatives) if response.top_recommendation is not None else 0} "
                f"recommendation options for request {simulation_request.request_id}."
            ),
            payload={
                "candidate_count": len(contexts),
                "top_station_id": top_station,
                "preference_mode": simulation_request.preference_mode,
                "recommendation_policy_name": recommendation_policy_name,
                "policy_source": response_metadata.get("policy_source"),
                "feeder_context_available": response_metadata.get("feeder_context_available"),
            },
        )
        return response

    def _build_simulation_request_from_external(self, request: ExternalChargingRequest) -> SimulationRequest:
        internal_request_id = request.request_id or f"external_{uuid4().hex[:12]}"
        arrival_ts = floor_to_timebase(request.request_timestamp)
        zone_id = request.zone_id or self._derive_zone_from_location(request.current_latitude, request.current_longitude)
        charger_preference = self._normalize_charger_type(request.charger_type)
        dwell_minutes = max(minutes_between(arrival_ts, ceil_to_timebase(request.latest_finish_ts)), TIME_STEP_MINUTES)
        return SimulationRequest(
            request_id=internal_request_id,
            client_request_id=request.client_request_id,
            source_type=request.source_type,
            arrival_ts=arrival_ts,
            latest_finish_ts=ceil_to_timebase(request.latest_finish_ts),
            requested_energy_kwh=float(request.requested_energy_kwh or 20.0),
            requested_duration_minutes=min(max(dwell_minutes // 2, TIME_STEP_MINUTES), dwell_minutes),
            preference_mode=request.preference_mode,
            charger_type_preference=charger_preference,
            current_latitude=request.current_latitude,
            current_longitude=request.current_longitude,
            zone_id=zone_id,
            target_soc=request.target_soc,
            current_soc=request.current_soc,
            battery_kwh=request.battery_kwh,
            vehicle_profile_id=request.vehicle_profile_id,
            vehicle_max_ac_kw=request.vehicle_max_ac_kw,
            vehicle_max_dc_kw=request.vehicle_max_dc_kw,
            metadata=request.metadata,
        )

    def step(self, action: dict[str, str] | list[AllocationDecision] | None = None) -> StepResult:
        """Advance the Dundee simulation by one 15-minute interval."""

        action_map = self._normalize_action(action)
        self.recent_events = []
        self.recently_completed_request_ids = []
        self.recently_missed_request_ids = []

        self._release_completed_sessions()
        self._activate_scheduled_background_requests()
        self._mark_expired_requests()
        self._allocate_pending_requests(action_map)
        self._start_queued_requests()
        self._mark_expired_requests()

        overloads = self._record_transformer_overloads()
        snapshot = self.get_state_snapshot()
        reward = RewardBreakdown(
            total=float(len(self.recently_completed_request_ids) - len(self.recently_missed_request_ids) - overloads),
            service_quality=float(len(self.recently_completed_request_ids) - len(self.recently_missed_request_ids)),
            grid_cost=float(-sum(snapshot.metrics.transformer_loading_kw.values()) / 1000.0),
            fairness=float(-snapshot.metrics.queue_length_total / 10.0),
        )
        self.current_time = advance_timebase(self.current_time)
        done = (
            self.replay_cursor >= len(self.replay_day_frame)
            and self.runtime_mode != "synthetic"
            and snapshot.metrics.active_request_count == 0
            and snapshot.metrics.queued_request_count == 0
        )
        return StepResult(
            observation=snapshot.model_dump(mode="json"),
            reward=reward,
            done=done,
            info={"events": [event.model_dump(mode="json") for event in self.recent_events]},
        )

    def get_state_snapshot(self) -> StateSnapshot:
        """Return a serializable snapshot of the current Dundee runtime state."""

        metrics = self._build_metrics_snapshot()
        active_requests: list[RequestSnapshot] = []
        queued_requests: list[RequestSnapshot] = []
        active_sessions: list[RequestSnapshot] = []
        for request in sorted(self.requests.values(), key=lambda item: (item.arrival_ts, item.request_id)):
            if request.status == "pending":
                active_requests.append(self._request_snapshot(request))
            elif request.status == "queued":
                queued_requests.append(self._request_snapshot(request))
            elif request.status == "charging":
                active_sessions.append(self._request_snapshot(request))
        stations = [self._station_snapshot(station_id) for station_id in sorted(self.station_index)]
        transformers = [self._transformer_snapshot(transformer_id) for transformer_id in sorted(self.transformer_index)]
        next_arrival = None
        if self.replay_cursor < len(self.replay_day_frame):
            next_arrival = self.replay_day_frame.iloc[self.replay_cursor]["arrival_slot"].to_pydatetime()
        return StateSnapshot(
            simulated_timestamp=self.current_time,
            active_policy=self.policy_mode,
            replay_year=self.replay_year,
            replay_day=self.replay_day.isoformat(),
            runtime_mode=self.runtime_mode,
            demand_multiplier=self.demand_multiplier,
            warm_start_minutes=self.warm_start_minutes,
            loop_running=False,
            loop_interval_seconds=0.0,
            operational_start_ts=self.operational_start_time,
            running=self.running,
            replay_cursor=self.replay_cursor,
            replay_total=len(self.replay_day_frame),
            next_replay_arrival_ts=next_arrival,
            latest_external_request_id=self.latest_external_request_id,
            active_requests=active_requests,
            queued_requests=queued_requests,
            active_sessions=active_sessions,
            recently_completed_request_ids=list(self.recently_completed_request_ids),
            recently_missed_request_ids=list(self.recently_missed_request_ids),
            stations=stations,
            transformers=transformers,
            metrics=metrics,
            metadata={
                "time_step_minutes": TIME_STEP_MINUTES,
                "replay_window_start": self.replay_window_start.isoformat(),
                "replay_window_end": self.replay_window_end.isoformat(),
                "synthetic_request_sequence": self.synthetic_request_sequence,
                "dynamic_pricing_enabled": self.dynamic_pricing_enabled,
            },
        )

    def get_recent_events(self) -> list[RuntimeEvent]:
        """Return the most recent step-local events."""

        return list(self.recent_events)

    def _build_station_index(self, bundle: DundeeDataBundle) -> dict[str, Station]:
        chargepoint_rows = []
        if getattr(bundle, "chargepoints", None) is not None:
            chargepoint_rows = bundle.chargepoints.to_dict(orient="records")
        chargepoints_by_station: dict[str, list[dict[str, Any]]] = {}
        for row in chargepoint_rows:
            chargepoints_by_station.setdefault(str(row.get("station_id", "")), []).append(row)
        stations: dict[str, Station] = {}
        station_rows = getattr(self, "topology_station_rows", bundle.stations)
        for row in station_rows.to_dict(orient="records"):
            station_id = str(row["station_id"])
            chargepoint_connectors = tuple(
                ChargingConnector(
                    connector_id=str(cp_row["cp_id"]),
                    cp_id=str(cp_row["cp_id"]),
                    connector_type=str(cp_row.get("connector_type_mode") or "unknown"),
                    max_power_kw=float(cp_row.get("assumed_port_kw") or 0.0),
                )
                for cp_row in chargepoints_by_station.get(station_id, [])
                if _optional_text(cp_row.get("cp_id")) is not None
            )
            if chargepoint_connectors:
                connectors = chargepoint_connectors
            else:
                connector_tokens = [
                    item.strip().lower()
                    for item in str(row["connector_mix_total"]).split(";")
                    if item and item.strip()
                ] or ["unknown"]
                cp_count_total = int(row["cp_count_total"])
                fallback_power_kw = float(row["station_capacity_kw_assumed"]) / max(cp_count_total, 1)
                connectors = tuple(
                    ChargingConnector(
                        connector_id=f"{station_id}_port_{idx + 1}",
                        max_power_kw=fallback_power_kw,
                        connector_type=connector_tokens[min(idx, len(connector_tokens) - 1)],
                    )
                    for idx in range(cp_count_total)
                )
            stations[station_id] = Station(
                station_id=station_id,
                station_name=str(row["station_name"]),
                zone_id=str(row["zone_id"]),
                transformer_id=str(row["transformer_id"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                cp_count_total=int(row["cp_count_total"]),
                connector_mix_total=str(row["connector_mix_total"]),
                station_capacity_kw_assumed=float(row["station_capacity_kw_assumed"]),
                connectors=connectors,
                is_public=_coerce_bool(row.get("is_public", True), default=True),
                is_fleet_only=_coerce_bool(row.get("is_fleet_only", False), default=False),
                requires_membership=_coerce_bool(row.get("requires_membership", False), default=False),
                needs_followup=_coerce_bool(row.get("needs_followup", False), default=False),
                exclude_from_recommendations=_coerce_bool(row.get("exclude_from_recommendations", False), default=False),
                access_notes=_optional_text(row.get("access_notes")),
            )
        return stations

    def _build_transformer_index(self, bundle: DundeeDataBundle) -> dict[str, Transformer]:
        station_rows = getattr(self, "topology_station_rows", bundle.stations)
        transformer_rows = getattr(self, "topology_transformer_rows", bundle.transformers)
        grouped_station_ids = station_rows.groupby("transformer_id")["station_id"].apply(list).to_dict()
        transformers: dict[str, Transformer] = {}
        for row in transformer_rows.to_dict(orient="records"):
            transformer_id = str(row["transformer_id"])
            transformers[transformer_id] = Transformer(
                transformer_id=transformer_id,
                transformer_name=str(row["transformer_name"]),
                zone_id=str(row["zone_id"]),
                capacity_kw=float(row["transformer_capacity_kw_assumed"]),
                attached_station_ids=tuple(grouped_station_ids.get(transformer_id, [])),
            )
        return transformers

    def _select_replay_table(self, replay_year: int):
        if replay_year == 2023:
            return self.bundle.replay_requests_2023
        if replay_year == 2024:
            return self.bundle.replay_requests_2024
        raise ValueError(f"Unsupported replay year: {replay_year}")

    def _slice_replay_window(self, window_start: datetime, window_end: datetime):
        frame = self.replay_requests.copy()
        mask = (frame["arrival_slot"] >= window_start) & (frame["arrival_slot"] <= window_end)
        return frame[mask].reset_index(drop=True)

    def _normalize_action(self, action: dict[str, str] | list[AllocationDecision] | None) -> dict[str, str]:
        if action is None:
            return {}
        if isinstance(action, dict):
            return {str(key): str(value) for key, value in action.items()}
        return {decision.request_id: decision.station_id for decision in action if decision.station_id}

    def _release_completed_sessions(self) -> None:
        for request_id, session in list(self.active_sessions.items()):
            if session.expected_completion_ts <= self.current_time:
                completed_request = self.requests.get(request_id)
                station_state = self.stations_runtime[session.station_id]
                if request_id in station_state.active_session_ids:
                    station_state.active_session_ids.remove(request_id)
                self.completed_requests_total += 1
                self.recently_completed_request_ids.append(request_id)
                self.active_sessions.pop(request_id, None)
                self.requests.pop(request_id, None)
                self._record_event(
                    "request_completed",
                    request_id=request_id,
                    station_id=session.station_id,
                    transformer_id=session.transformer_id,
                    zone_id=self.station_index[session.station_id].zone_id,
                    source_type=completed_request.source_type if completed_request is not None else None,
                    summary="Charging request completed at its assigned station.",
                )

    def _activate_scheduled_background_requests(self) -> None:
        if self.runtime_mode in {"replay", "hybrid"}:
            self._activate_scheduled_replay_requests()
        if self.runtime_mode in {"synthetic", "hybrid"}:
            self._activate_synthetic_requests()

    def _activate_scheduled_replay_requests(self) -> None:
        while self.replay_cursor < len(self.replay_day_frame):
            row = self.replay_day_frame.iloc[self.replay_cursor]
            arrival_slot = row["arrival_slot"].to_pydatetime()
            if arrival_slot > self.current_time:
                break
            request = SimulationRequest(
                request_id=str(row["request_id"]),
                client_request_id=None,
                source_type="replay_background",
                arrival_ts=row["arrival_ts"].to_pydatetime(),
                latest_finish_ts=row["latest_finish_slot"].to_pydatetime(),
                requested_energy_kwh=float(row["requested_energy_kwh"]),
                requested_duration_minutes=int(row["requested_duration_minutes"]),
                preference_mode=str(row["user_preference_mode"]),
                charger_type_preference=str(row["charger_type_preference"]),
                zone_id=str(row["zone_id"]),
                source_session_id=str(row["source_session_id"]),
                metadata={"replay_station_id": str(row["station_id"])},
            )
            self.requests[request.request_id] = request
            self.requests_seen_total += 1
            self.replay_cursor += 1
            self._record_event(
                "replay_request_arrived",
                request_id=request.request_id,
                station_id=str(row["station_id"]),
                transformer_id=str(row["transformer_id"]),
                zone_id=request.zone_id,
                source_type=request.source_type,
                summary="Replay background request entered the simulator.",
            )

    def _activate_synthetic_requests(self) -> None:
        request_count = self._synthetic_request_count_for_slot(self.current_time)
        for request_index in range(request_count):
            request = self._build_synthetic_request(self.current_time, request_index)
            self.requests[request.request_id] = request
            self.requests_seen_total += 1
            self._record_event(
                "synthetic_request_arrived",
                request_id=request.request_id,
                station_id=request.metadata.get("synthetic_anchor_station_id"),
                transformer_id=request.metadata.get("synthetic_anchor_transformer_id"),
                zone_id=request.zone_id,
                source_type=request.source_type,
                summary="Synthetic background request entered the simulator.",
                payload={"demand_multiplier": self.demand_multiplier},
            )

    def _synthetic_request_count_for_slot(self, slot_ts: datetime) -> int:
        arrival = self.request_generator_params["arrival_distributions"]
        base_daily_requests = float(self.request_generator_params["request_counts_by_year"].get(str(self.replay_year), 0)) / 366.0
        hour_share = float(arrival["hour_share"].get(str(slot_ts.hour), 1.0 / 24.0))
        month_share = float(arrival["month_share"].get(str(slot_ts.month), 1.0 / 12.0)) * 12.0
        weekday_type = "weekend" if slot_ts.weekday() >= 5 else "weekday"
        weekday_share = float(arrival["weekday_type_share"].get(weekday_type, 0.5))
        weekday_norm = 2.0 / 7.0 if weekday_type == "weekend" else 5.0 / 7.0
        slot_expectation = base_daily_requests * hour_share * month_share * (weekday_share / max(weekday_norm, 0.01)) / 4.0
        slot_expectation *= self.demand_multiplier
        integer = int(slot_expectation)
        fractional = max(slot_expectation - integer, 0.0)
        return integer + int(self._stable_bucket(f"{slot_ts.isoformat()}|count") < fractional)

    def _build_synthetic_request(self, slot_ts: datetime, request_index: int) -> SimulationRequest:
        zone_id = self._weighted_choice(
            self.request_generator_params["zone_level_demand_share"]["request_share"],
            seed=f"{slot_ts.isoformat()}|zone|{request_index}",
        )
        stations_in_zone = [
            station for station in self.station_index.values() if station.zone_id == zone_id
        ] or list(self.station_index.values())
        station_weights = {
            station.station_id: max(float(station.cp_count_total), 1.0)
            for station in stations_in_zone
        }
        anchor_station_id = self._weighted_choice(
            station_weights,
            seed=f"{slot_ts.isoformat()}|station|{request_index}",
        )
        anchor_station = self.station_index[anchor_station_id]
        energy_summary = self.request_generator_params["requested_energy_kwh_summary"]
        duration_summary = self.request_generator_params["requested_duration_minutes_summary"]
        slack_summary = self.request_generator_params["slack_minutes_summary"]
        requested_energy = self._bucket_sample(
            [
                float(energy_summary["p10"]),
                float(energy_summary["p25"]),
                float(energy_summary["median"]),
                float(energy_summary["p75"]),
                float(energy_summary["p90"]),
                float(energy_summary["p95"]),
            ],
            seed=f"{slot_ts.isoformat()}|energy|{request_index}",
        )
        requested_duration = int(
            self._bucket_sample(
                [
                    float(duration_summary["p10"]),
                    float(duration_summary["p25"]),
                    float(duration_summary["median"]),
                    float(duration_summary["p75"]),
                    float(duration_summary["p90"]),
                    float(duration_summary["p95"]),
                ],
                seed=f"{slot_ts.isoformat()}|duration|{request_index}",
            )
        )
        slack_minutes = int(
            self._bucket_sample(
                [
                    float(slack_summary["p10"]),
                    float(slack_summary["p25"]),
                    float(slack_summary["median"]),
                    float(slack_summary["p75"]),
                    float(slack_summary["p90"]),
                    float(slack_summary["p95"]),
                ],
                seed=f"{slot_ts.isoformat()}|slack|{request_index}",
            )
        )
        preference_mode = self._weighted_choice(
            self.request_generator_params["user_preference_mode"]["realized_share"],
            seed=f"{slot_ts.isoformat()}|preference|{request_index}",
        )
        charger_preference = "Rapid" if {"rapid", "ultra_rapid"} & {
            item.strip().lower() for item in anchor_station.connector_mix_total.split(";") if item.strip()
        } else "AC"
        latest_finish_ts = slot_ts + timedelta(minutes=requested_duration + slack_minutes)
        self.synthetic_request_sequence += 1
        request_id = f"synthetic_{slot_ts.strftime('%Y%m%d%H%M')}_{self.synthetic_request_sequence:04d}"
        return SimulationRequest(
            request_id=request_id,
            client_request_id=None,
            source_type="synthetic_background",
            arrival_ts=slot_ts,
            latest_finish_ts=ceil_to_timebase(latest_finish_ts),
            requested_energy_kwh=max(round(requested_energy, 3), 1.0),
            requested_duration_minutes=max(int(round(requested_duration / TIME_STEP_MINUTES) * TIME_STEP_MINUTES), TIME_STEP_MINUTES),
            preference_mode=str(preference_mode),
            charger_type_preference=charger_preference,
            zone_id=anchor_station.zone_id,
            current_latitude=anchor_station.latitude,
            current_longitude=anchor_station.longitude,
            metadata={
                "synthetic_anchor_station_id": anchor_station.station_id,
                "synthetic_anchor_transformer_id": anchor_station.transformer_id,
                "demand_multiplier": self.demand_multiplier,
            },
        )

    def _mark_expired_requests(self) -> None:
        for request in list(self.requests.values()):
            if request.status in {"completed", "missed"}:
                continue
            if self.current_time >= request.latest_finish_ts and request.status != "charging":
                self._mark_request_missed(request, reason="latest_finish_missed")

    def _allocate_pending_requests(self, action_map: dict[str, str]) -> None:
        pending = [request for request in self.requests.values() if request.status == "pending" and request.arrival_ts <= self.current_time]
        pending.sort(key=lambda item: (item.source_type != "external_live", item.arrival_ts, item.request_id))
        policy = get_policy(self.policy_mode)
        for request in pending:
            recommendations = self.get_ranked_recommendations(request)
            options = [option for option in [recommendations.top_recommendation, *recommendations.alternatives] if option is not None]
            if not options:
                self._mark_request_missed(request, reason="no_feasible_station")
                continue
            chosen_option = None
            if request.request_id in action_map:
                chosen_option = next((option for option in options if option.station_id == action_map[request.request_id]), None)
            if chosen_option is None:
                chosen_option = policy.select_option(request, options)
            if chosen_option is None:
                self._mark_request_missed(request, reason="policy_returned_no_station")
                continue
            request.assigned_station_id = chosen_option.station_id
            request.assigned_transformer_id = chosen_option.transformer_id
            self._record_event(
                "request_assigned",
                request_id=request.request_id,
                station_id=chosen_option.station_id,
                transformer_id=chosen_option.transformer_id,
                zone_id=chosen_option.zone_id,
                source_type=request.source_type,
                summary="Request assigned to a candidate station by the active policy.",
                payload={"score": chosen_option.score},
            )
            if self._can_start_now(request, chosen_option):
                self._start_session(request, chosen_option)
            else:
                self._enqueue_request(request, chosen_option)

    def _start_queued_requests(self) -> None:
        for station_id in sorted(self.stations_runtime):
            station_state = self.stations_runtime[station_id]
            while station_state.queue_request_ids and self._station_free_ports(station_id) > 0:
                request_id = station_state.queue_request_ids[0]
                request = self.requests.get(request_id)
                if request is None:
                    station_state.queue_request_ids.pop(0)
                    continue
                option = self._station_specific_option(request, station_id)
                if option is None:
                    station_state.queue_request_ids.pop(0)
                    self._mark_request_missed(request, reason="queue_cannot_meet_deadline")
                    continue
                if not self._can_start_now(request, option):
                    break
                station_state.queue_request_ids.pop(0)
                self._start_session(request, option)

    def _enqueue_request(self, request: SimulationRequest, option) -> None:
        station_state = self.stations_runtime[option.station_id]
        if request.request_id not in station_state.queue_request_ids:
            station_state.queue_request_ids.append(request.request_id)
        request.status = "queued"
        request.queue_entered_ts = self.current_time
        self._record_event(
            "request_queued",
            request_id=request.request_id,
            station_id=option.station_id,
            transformer_id=option.transformer_id,
            zone_id=option.zone_id,
            source_type=request.source_type,
            summary="Request queued at the selected station.",
        )

    def _start_session(self, request: SimulationRequest, option) -> None:
        assigned_power_kw = max(request.requested_energy_kwh * 60.0 / max(option.estimated_duration_minutes, TIME_STEP_MINUTES), 1.0)
        expected_completion = advance_timebase(self.current_time, steps=option.estimated_duration_minutes // TIME_STEP_MINUTES)
        request.status = "charging"
        request.started_at = self.current_time
        request.expected_completion_ts = expected_completion
        request.remaining_minutes = option.estimated_duration_minutes
        station_state = self.stations_runtime[option.station_id]
        connector = self._select_connector_for_request(request, option.station_id)
        if request.request_id not in station_state.active_session_ids:
            station_state.active_session_ids.append(request.request_id)
        self.active_sessions[request.request_id] = ActiveChargingSession(
            request_id=request.request_id,
            station_id=option.station_id,
            transformer_id=option.transformer_id,
            started_at=self.current_time,
            expected_completion_ts=expected_completion,
            assigned_power_kw=assigned_power_kw,
            estimated_cost_gbp=option.estimated_cost_gbp,
            connector_id=connector.connector_id if connector is not None else None,
            connector_type=connector.connector_type if connector is not None else None,
        )
        self._record_event(
            "request_started",
            request_id=request.request_id,
            station_id=option.station_id,
            transformer_id=option.transformer_id,
            zone_id=option.zone_id,
            source_type=request.source_type,
            summary="Request started charging at the selected station.",
            payload={"assigned_power_kw": assigned_power_kw},
        )

    def _can_start_now(self, request: SimulationRequest, option) -> bool:
        minutes_to_deadline = max(minutes_between(self.current_time, request.latest_finish_ts), 0)
        if option.estimated_duration_minutes > max(minutes_to_deadline, TIME_STEP_MINUTES):
            return False
        headroom = self._current_transformer_headroom(option.transformer_id)
        required_power = max(request.requested_energy_kwh * 60.0 / max(option.estimated_duration_minutes, TIME_STEP_MINUTES), 1.0)
        return self._station_free_compatible_ports(option.station_id, request.charger_type_preference) > 0 and headroom >= required_power

    def _station_free_ports(self, station_id: str) -> int:
        station = self.station_index[station_id]
        active = len(self.stations_runtime[station_id].active_session_ids)
        if station.connectors:
            if self._has_generic_busy_sessions(station_id):
                return max(station.cp_count_total - active, 0)
            return max(len(station.connectors) - len(self._busy_connector_ids(station_id)), 0)
        return max(station.cp_count_total - active, 0)

    def _station_free_compatible_ports(self, station_id: str, requested_type: str) -> int:
        station = self.station_index[station_id]
        compatible = self._compatible_connectors(station, requested_type)
        if not compatible:
            return 0
        if self._has_generic_busy_sessions(station_id):
            return min(self._station_free_ports(station_id), len(compatible))
        return len(self._available_compatible_connectors(station_id, requested_type))

    def _station_specific_option(self, request: SimulationRequest, station_id: str):
        options = self._build_candidate_contexts(request, only_station_id=station_id)
        response = self.recommendation_service.recommend(
            request_id=request.request_id,
            client_request_id=request.client_request_id,
            simulated_timestamp=self.current_time,
            zone_id=request.zone_id,
            source_type=request.source_type,
            preference_mode=request.preference_mode,
            candidate_contexts=options,
        )
        self._record_event(
            "recommendation_generated",
            request_id=request.request_id,
            station_id=response.top_recommendation.station_id if response.top_recommendation is not None else None,
            transformer_id=response.top_recommendation.transformer_id if response.top_recommendation is not None else None,
            zone_id=request.zone_id,
            source_type=request.source_type,
            summary="Generated a station-specific recommendation for a queued request.",
            payload={"candidate_count": len(options)},
        )
        return response.top_recommendation

    def _build_candidate_contexts(self, request: SimulationRequest, only_station_id: str | None = None) -> list[CandidateContext]:
        self._route_estimate_cache = {}
        self.last_routing_fallback_reason = None
        return self.candidate_builder.build(
            request=request,
            stations=self.station_index.values(),
            stations_runtime=self.stations_runtime,
            current_time=self.current_time,
            only_station_id=only_station_id,
            distance_to_station_km=self._distance_to_station_km,
            estimate_station_wait_minutes=self._estimate_station_wait_minutes,
            current_price_per_kwh=self._current_price_per_kwh,
            station_price_per_kwh=lambda station_id, _request=request: self._candidate_station_price_per_kwh(
                _request,
                self.station_index[station_id],
            ),
            station_pricing_metadata=lambda station_id, _request=request: self._candidate_station_pricing_metadata(
                _request,
                self.station_index[station_id],
            ),
            current_transformer_headroom=self._current_transformer_headroom,
            is_charger_compatible=self._is_charger_compatible,
            station_eligibility_filter=getattr(self, "station_eligibility_filter", StationEligibilityFilter()),
            station_effective_power_kw=self._best_available_connector_power_kw,
            compatible_available_port_count=self._compatible_available_port_count,
        )

    def _estimate_station_wait_minutes(self, station_id: str) -> int:
        station_state = self.stations_runtime[station_id]
        free_ports = self._station_free_ports(station_id)
        if free_ports > 0 and not station_state.queue_request_ids:
            return 0
        durations: list[int] = []
        for request_id in station_state.active_session_ids:
            request = self.requests.get(request_id)
            if request and request.expected_completion_ts is not None:
                durations.append(max(minutes_between(self.current_time, request.expected_completion_ts), 0))
        earliest_release = min(durations) if durations else TIME_STEP_MINUTES
        return int(earliest_release + (len(station_state.queue_request_ids) * TIME_STEP_MINUTES))

    def _current_transformer_context(self, transformer_id: str) -> GridContext:
        timestamps = (self.current_time,)
        background = self.forecast_provider.forecast_background_load(
            ForecastRequest(series_name=transformer_id, timestamps=timestamps, default_value=0.0)
        ).values[0]
        price = self.forecast_provider.forecast_price(
            ForecastRequest(series_name="system", timestamps=timestamps, default_value=0.25)
        ).values[0]
        pv_norm = self.forecast_provider.forecast_pv_generation(
            ForecastRequest(series_name="system", timestamps=timestamps, default_value=0.0)
        ).values[0]
        transformer = self.transformer_index[transformer_id]
        pv_generation_kw = float(pv_norm) * (transformer.capacity_kw / 1000.0) * 0.15
        return GridContext(
            interval_start=self.current_time,
            background_load_kw=float(background),
            tariff_per_kwh=float(price),
            pv_generation_kw=float(pv_generation_kw),
        )

    def _current_transformer_headroom(self, transformer_id: str) -> float:
        transformer = self.transformer_index[transformer_id]
        context = self._current_transformer_context(transformer_id)
        ev_load = sum(session.assigned_power_kw for session in self.active_sessions.values() if session.transformer_id == transformer_id)
        return float(transformer.capacity_kw - max(context.background_load_kw - context.pv_generation_kw, 0.0) - ev_load)

    def _current_transformer_net_load_kw(self, transformer_id: str) -> float:
        return float(self._transformer_snapshot(transformer_id).net_load_kw)

    def _current_price_per_kwh(self) -> float:
        return float(
            self.forecast_provider.forecast_price(
                ForecastRequest(series_name="system", timestamps=(self.current_time,), default_value=0.25)
            ).values[0]
        )

    def _current_station_pricing_result(self, station_id: str) -> DynamicPricingResult:
        station = self.station_index[station_id]
        station_state = self.stations_runtime[station_id]
        transformer_state = self._transformer_snapshot(station.transformer_id)
        base_price = self._station_default_base_price_per_kwh(station)
        return calculate_dynamic_price(
            DynamicPricingInput(
                base_price_per_kwh=base_price,
                transformer_capacity_kw=transformer_state.capacity_kw,
                transformer_net_load_kw=transformer_state.net_load_kw,
                transformer_headroom_kw=transformer_state.headroom_kw,
                station_queue_length=len(station_state.queue_request_ids),
                station_utilization=len(station_state.active_session_ids) / max(station.cp_count_total, 1),
                dynamic_pricing_enabled=self.dynamic_pricing_enabled,
            )
        )

    def _current_station_price_per_kwh(self, station_id: str) -> float:
        return float(self._current_station_pricing_result(station_id).dynamic_price_per_kwh)

    def _current_station_pricing_metadata(self, station_id: str) -> dict[str, Any]:
        result = self._current_station_pricing_result(station_id)
        return {
            "pricing_model": "dundee_tariff_plus_dynamic_overlay",
            "base_price_per_kwh": round(result.base_price_per_kwh, 4),
            "final_price_per_kwh": round(result.dynamic_price_per_kwh, 4),
            "dynamic_pricing_enabled": self.dynamic_pricing_enabled,
            "total_dynamic_multiplier": round(result.total_multiplier, 4),
            "transformer_multiplier": round(result.transformer_multiplier, 4),
            "congestion_multiplier": round(result.congestion_multiplier, 4),
            "transformer_load_ratio": round(result.load_ratio, 4),
            "transformer_headroom_ratio": round(result.headroom_ratio, 4),
            "pricing_reason": result.reason,
        }

    def _transformer_snapshot(self, transformer_id: str) -> TransformerStateSnapshot:
        transformer = self.transformer_index[transformer_id]
        context = self._current_transformer_context(transformer_id)
        ev_load = sum(session.assigned_power_kw for session in self.active_sessions.values() if session.transformer_id == transformer_id)
        net_load = max(context.background_load_kw - context.pv_generation_kw, 0.0) + ev_load
        headroom = transformer.capacity_kw - net_load
        return TransformerStateSnapshot(
            transformer_id=transformer.transformer_id,
            transformer_name=transformer.transformer_name,
            zone_id=transformer.zone_id,
            capacity_kw=transformer.capacity_kw,
            background_load_kw=context.background_load_kw,
            ev_load_kw=ev_load,
            pv_generation_kw=context.pv_generation_kw,
            net_load_kw=net_load,
            headroom_kw=headroom,
            overload=headroom < 0,
            attached_station_ids=list(transformer.attached_station_ids),
        )

    def _station_snapshot(self, station_id: str) -> StationStateSnapshot:
        station = self.station_index[station_id]
        station_state = self.stations_runtime[station_id]
        return StationStateSnapshot(
            station_id=station.station_id,
            station_name=station.station_name,
            zone_id=station.zone_id,
            transformer_id=station.transformer_id,
            latitude=station.latitude,
            longitude=station.longitude,
            cp_count_total=station.cp_count_total,
            station_capacity_kw_assumed=station.station_capacity_kw_assumed,
            active_sessions=len(station_state.active_session_ids),
            queue_length=len(station_state.queue_request_ids),
            utilization=len(station_state.active_session_ids) / max(station.cp_count_total, 1),
            estimated_wait_minutes=self._estimate_station_wait_minutes(station_id),
            transformer_headroom_kw=self._current_transformer_headroom(station.transformer_id),
            active_request_ids=list(station_state.active_session_ids),
            queued_request_ids=list(station_state.queue_request_ids),
        )

    def _request_snapshot(self, request: SimulationRequest) -> RequestSnapshot:
        station_name = self.station_index[request.assigned_station_id].station_name if request.assigned_station_id else None
        remaining_minutes = None
        if request.expected_completion_ts is not None:
            remaining_minutes = max(minutes_between(self.current_time, request.expected_completion_ts), 0)
        return RequestSnapshot(
            request_id=request.request_id,
            client_request_id=request.client_request_id,
            source_type=request.source_type,
            status=request.status,
            arrival_ts=request.arrival_ts,
            latest_finish_ts=request.latest_finish_ts,
            requested_energy_kwh=request.requested_energy_kwh,
            requested_duration_minutes=request.requested_duration_minutes,
            preference_mode=request.preference_mode,
            charger_type_preference=request.charger_type_preference,
            station_id=request.assigned_station_id,
            station_name=station_name,
            transformer_id=request.assigned_transformer_id,
            zone_id=request.zone_id,
            queue_entered_ts=request.queue_entered_ts,
            started_at=request.started_at,
            expected_completion_ts=request.expected_completion_ts,
            remaining_minutes=remaining_minutes,
            metadata=request.metadata,
        )

    def _build_metrics_snapshot(self) -> MetricsSnapshot:
        queue_by_zone: dict[str, int] = {}
        requests_by_zone: dict[str, int] = {}
        for request in self.requests.values():
            zone_id = request.zone_id or "unknown"
            requests_by_zone[zone_id] = requests_by_zone.get(zone_id, 0) + 1
            if request.status == "queued":
                queue_by_zone[zone_id] = queue_by_zone.get(zone_id, 0) + 1
        transformer_states = [self._transformer_snapshot(transformer_id) for transformer_id in self.transformer_index]
        return MetricsSnapshot(
            simulated_timestamp=self.current_time,
            active_policy=self.policy_mode,
            active_request_count=sum(1 for request in self.requests.values() if request.status == "pending"),
            queued_request_count=sum(1 for request in self.requests.values() if request.status == "queued"),
            active_session_count=len(self.active_sessions),
            completed_requests_total=self.completed_requests_total,
            missed_requests_total=self.missed_requests_total,
            overload_event_count=self.overload_event_count,
            queue_length_total=sum(len(state.queue_request_ids) for state in self.stations_runtime.values()),
            requests_seen_total=self.requests_seen_total,
            queue_length_by_zone=queue_by_zone,
            requests_by_zone=requests_by_zone,
            transformer_loading_kw={state.transformer_id: round(state.net_load_kw, 3) for state in transformer_states},
            transformer_headroom_kw={state.transformer_id: round(state.headroom_kw, 3) for state in transformer_states},
        )

    def _record_transformer_overloads(self) -> int:
        overloads = 0
        for transformer_id in self.transformer_index:
            state = self._transformer_snapshot(transformer_id)
            if state.overload:
                overloads += 1
                self.overload_event_count += 1
                self._record_event(
                    "transformer_overload_warning",
                    transformer_id=transformer_id,
                    zone_id=state.zone_id,
                    severity="warning",
                    summary="Synthetic transformer headroom dropped below zero.",
                )
        return overloads

    def _record_event(
        self,
        event_type: str,
        *,
        severity: str = "info",
        request_id: str | None = None,
        station_id: str | None = None,
        transformer_id: str | None = None,
        zone_id: str | None = None,
        source_type: str | None = None,
        summary: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.recent_events.append(
            RuntimeEvent(
                event_id=f"evt_{uuid4().hex[:12]}",
                event_type=event_type,
                occurred_at=datetime.now(UTC),
                simulated_timestamp=self.current_time,
                severity=severity,
                request_id=request_id,
                station_id=station_id,
                transformer_id=transformer_id,
                zone_id=zone_id,
                source_type=source_type,
                summary=summary,
                message=summary,
                payload=payload or {},
            )
        )

    def _mark_request_missed(self, request: SimulationRequest, *, reason: str) -> None:
        if request.assigned_station_id:
            station_state = self.stations_runtime[request.assigned_station_id]
            if request.request_id in station_state.queue_request_ids:
                station_state.queue_request_ids.remove(request.request_id)
        self.missed_requests_total += 1
        self.recently_missed_request_ids.append(request.request_id)
        self.requests.pop(request.request_id, None)
        self._record_event(
            "request_missed",
            request_id=request.request_id,
            station_id=request.assigned_station_id,
            transformer_id=request.assigned_transformer_id,
            zone_id=request.zone_id,
            source_type=request.source_type,
            severity="warning",
            summary="Request could not be served before its latest finish timestamp.",
            payload={"reason": reason},
        )

    def _stable_bucket(self, seed: str) -> float:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:12], 16) / float(16**12)

    def _weighted_choice(self, weights: dict[str, float], *, seed: str) -> str:
        total = sum(max(float(value), 0.0) for value in weights.values())
        if total <= 0:
            return next(iter(weights))
        bucket = self._stable_bucket(seed)
        cumulative = 0.0
        for key, value in sorted(weights.items()):
            cumulative += max(float(value), 0.0) / total
            if bucket <= cumulative:
                return key
        return next(reversed(sorted(weights)))

    def _bucket_sample(self, values: list[float], *, seed: str) -> float:
        ordered = sorted(float(value) for value in values)
        if not ordered:
            return 0.0
        bucket = self._stable_bucket(seed)
        index = min(int(bucket * len(ordered)), len(ordered) - 1)
        return ordered[index]

    def _normalize_charger_type(self, charger_type: str) -> str:
        value = str(charger_type or "Any").strip().lower()
        if value in {"dc", "rapid", "ultra_rapid", "ultrarapid"}:
            return "Rapid"
        if value in {"ac"}:
            return "AC"
        return "Any"

    def _normalize_connector_type(self, connector_type: str) -> str:
        value = str(connector_type or "unknown").strip().lower()
        if value in {"ultra_rapid", "ultrarapid"}:
            return "ultra_rapid"
        if value in {"rapid", "dc"}:
            return "rapid"
        if value == "ac":
            return "ac"
        return value or "unknown"

    def _connector_type_compatible(self, requested_type: str, connector_type: str) -> bool:
        desired = str(requested_type or "Any").strip().lower()
        available = self._normalize_connector_type(connector_type)
        if desired in {"any", ""}:
            return True
        if desired in {"rapid", "dc"}:
            return available in {"rapid", "ultra_rapid"}
        if desired in {"ultra_rapid", "ultrarapid"}:
            return available == "ultra_rapid"
        if desired == "ac":
            return available == "ac"
        return desired == available

    def _compatible_connectors(self, station: Station, requested_type: str) -> list[ChargingConnector]:
        return [
            connector
            for connector in station.connectors
            if self._connector_type_compatible(requested_type, connector.connector_type)
        ]

    def _busy_connector_ids(self, station_id: str) -> set[str]:
        busy: set[str] = set()
        for request_id in self.stations_runtime[station_id].active_session_ids:
            session = self.active_sessions.get(request_id)
            if session is not None and session.connector_id:
                busy.add(session.connector_id)
        return busy

    def _has_generic_busy_sessions(self, station_id: str) -> bool:
        for request_id in self.stations_runtime[station_id].active_session_ids:
            session = self.active_sessions.get(request_id)
            if session is None or session.connector_id is None:
                return True
        return False

    def _available_compatible_connectors(self, station_id: str, requested_type: str) -> list[ChargingConnector]:
        station = self.station_index[station_id]
        compatible = self._compatible_connectors(station, requested_type)
        if self._has_generic_busy_sessions(station_id):
            return compatible[: min(self._station_free_ports(station_id), len(compatible))]
        busy = self._busy_connector_ids(station_id)
        return [connector for connector in compatible if connector.connector_id not in busy]

    def _compatible_available_port_count(self, request: SimulationRequest, station: Station) -> int:
        return len(self._available_compatible_connectors(station.station_id, request.charger_type_preference))

    def _best_available_connector_power_kw(self, request: SimulationRequest, station: Station) -> float:
        connector = self._select_recommendation_connector(request, station)
        if connector is None:
            return estimate_effective_power_kw(request, station)
        return estimate_connector_effective_power_kw(request, connector)

    def _select_connector_for_request(self, request: SimulationRequest, station_id: str) -> ChargingConnector | None:
        station = self.station_index[station_id]
        return self._select_recommendation_connector(request, station)

    def _select_recommendation_connector(self, request: SimulationRequest, station: Station) -> ChargingConnector | None:
        available = self._available_compatible_connectors(station.station_id, request.charger_type_preference)
        if not available:
            return None
        return max(
            available,
            key=lambda connector: (
                estimate_connector_effective_power_kw(request, connector),
                connector.max_power_kw,
                connector.connector_id,
            ),
        )

    def _station_default_base_price_per_kwh(self, station: Station) -> float:
        representative = max(
            station.connectors or (
                ChargingConnector(
                    connector_id=f"{station.station_id}_default",
                    connector_type="unknown",
                    max_power_kw=station.average_port_power_kw,
                ),
            ),
            key=lambda connector: (float(getattr(connector, "max_power_kw", 0.0)), str(getattr(connector, "connector_type", ""))),
        )
        return float(
            build_dundee_tariff_metadata(
                connector_type=representative.connector_type,
                power_kw=representative.max_power_kw,
            )["base_price_per_kwh"]
        )

    def _candidate_station_price_per_kwh(self, request: SimulationRequest, station: Station) -> float:
        return float(self._candidate_station_pricing_result(request, station).dynamic_price_per_kwh)

    def _candidate_station_pricing_result(self, request: SimulationRequest, station: Station) -> DynamicPricingResult:
        connector = self._select_recommendation_connector(request, station)
        connector_type = connector.connector_type if connector is not None else station.connector_mix_total
        connector_power_kw = (
            float(connector.max_power_kw)
            if connector is not None
            else max(float(station.average_port_power_kw), 7.0)
        )
        base_price = float(
            build_dundee_tariff_metadata(
                connector_type=connector_type,
                power_kw=connector_power_kw,
            )["base_price_per_kwh"]
        )
        transformer_state = self._transformer_snapshot(station.transformer_id)
        station_state = self.stations_runtime[station.station_id]
        return calculate_dynamic_price(
            DynamicPricingInput(
                base_price_per_kwh=base_price,
                transformer_capacity_kw=transformer_state.capacity_kw,
                transformer_net_load_kw=transformer_state.net_load_kw,
                transformer_headroom_kw=transformer_state.headroom_kw,
                station_queue_length=len(station_state.queue_request_ids),
                station_utilization=len(station_state.active_session_ids) / max(station.cp_count_total, 1),
                dynamic_pricing_enabled=self.dynamic_pricing_enabled,
            )
        )

    def _candidate_station_pricing_metadata(self, request: SimulationRequest, station: Station) -> dict[str, Any]:
        connector = self._select_recommendation_connector(request, station)
        connector_type = connector.connector_type if connector is not None else station.connector_mix_total
        connector_power_kw = (
            float(connector.max_power_kw)
            if connector is not None
            else max(float(station.average_port_power_kw), 7.0)
        )
        effective_power_kw = (
            estimate_connector_effective_power_kw(request, connector)
            if connector is not None
            else estimate_effective_power_kw(request, station)
        )
        tariff_metadata = build_dundee_tariff_metadata(
            connector_type=connector_type,
            power_kw=connector_power_kw,
        )
        pricing_result = self._candidate_station_pricing_result(request, station)
        route_metadata = self._route_metadata_for_station(request, station)
        return {
            "pricing_model": "dundee_tariff_plus_dynamic_overlay",
            "tariff_class": tariff_metadata["tariff_class"],
            "base_price_per_kwh": round(pricing_result.base_price_per_kwh, 4),
            "final_price_per_kwh": round(pricing_result.dynamic_price_per_kwh, 4),
            "price_per_kwh": round(pricing_result.dynamic_price_per_kwh, 4),
            "dynamic_pricing_enabled": self.dynamic_pricing_enabled,
            "total_dynamic_multiplier": round(pricing_result.total_multiplier, 4),
            "transformer_multiplier": round(pricing_result.transformer_multiplier, 4),
            "congestion_multiplier": round(pricing_result.congestion_multiplier, 4),
            "transformer_load_ratio": round(pricing_result.load_ratio, 4),
            "transformer_headroom_ratio": round(pricing_result.headroom_ratio, 4),
            "connection_fee_gbp": 0.0,
            "pricing_source": "dundee_simplified_tariff_v1",
            "pricing_reason": pricing_result.reason,
            "tariff_fallback_used": bool(tariff_metadata["tariff_fallback_used"]),
            "selected_connector_type": connector_type,
            "selected_connector_power_kw": round(connector_power_kw, 3),
            "selected_connector_id": connector.connector_id if connector is not None else None,
            "effective_power_kw": round(float(effective_power_kw), 3),
            **route_metadata,
        }

    def _estimate_route(self, request: SimulationRequest, station: Station) -> RouteEstimate:
        if not hasattr(self, "_route_estimate_cache"):
            self._route_estimate_cache = {}
        if not hasattr(self, "last_routing_fallback_reason"):
            self.last_routing_fallback_reason = None
        request_id = request.request_id or f"{request.arrival_ts.isoformat()}_{request.client_request_id}"
        cache_key = (request_id, station.station_id)
        if cache_key not in self._route_estimate_cache:
            estimate = self.routing_provider.estimate_route(request, station)
            metadata = estimate.metadata or {}
            self.last_routing_fallback_reason = metadata.get("fallback_reason") if metadata.get("fallback_used") else None
            self._route_estimate_cache[cache_key] = estimate
        return self._route_estimate_cache[cache_key]

    def _route_metadata_for_station(self, request: SimulationRequest, station: Station) -> dict[str, Any]:
        estimate = self._estimate_route(request, station)
        metadata = dict(estimate.metadata or {})
        return {
            "routing_provider_name": estimate.provider,
            "route_distance_km": round(float(estimate.distance_km), 4),
            "route_duration_minutes": None if estimate.duration_minutes is None else round(float(estimate.duration_minutes), 3),
            "routing_fallback_used": bool(metadata.get("fallback_used", False)),
            "routing_fallback_reason": metadata.get("fallback_reason"),
            "routing_provider_requested": metadata.get("provider_requested", estimate.provider),
        }

    def _is_charger_compatible(self, requested_type: str, connector_mix_total: str) -> bool:
        desired = str(requested_type or "Any").strip().lower()
        available = {item.strip().lower() for item in str(connector_mix_total).split(";") if item.strip()}
        if desired in {"any", ""}:
            return True
        if desired in {"rapid", "dc"}:
            return bool({"rapid", "ultra_rapid"} & available)
        if desired in {"ultra_rapid", "ultrarapid"}:
            return "ultra_rapid" in available
        return desired in available

    def _derive_zone_from_location(self, latitude: float | None, longitude: float | None) -> str:
        nearest_station = min(
            self.station_index.values(),
            key=lambda station: self._distance_simple(latitude, longitude, station.latitude, station.longitude),
        )
        return nearest_station.zone_id

    def _distance_to_station_km(self, request: SimulationRequest, station: Station) -> float:
        return float(self._estimate_route(request, station).distance_km)

    def _distance_simple(self, lat_a: float | None, lon_a: float | None, lat_b: float, lon_b: float) -> float:
        return simple_distance_km(lat_a, lon_a, lat_b, lon_b)


__all__ = ["DundeeEnv", "policy_requires_feeder_context"]
