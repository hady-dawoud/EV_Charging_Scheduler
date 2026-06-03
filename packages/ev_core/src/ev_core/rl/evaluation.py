"""Lightweight deterministic-baseline evaluation harness for RL preparation."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from time import perf_counter

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.env.environment import DundeeEnv
from ev_core.routing.osmnx_provider import OSMnxRoutingProvider
from ev_core.routing.simple_distance import SimpleDistanceRoutingProvider
from ev_core.topology.scenarios import TopologyScenario
from ev_core.utils.timebase import floor_to_timebase

from .baselines import RandomValidPolicy
from .contracts import EvaluationMetrics, RLEpisodeScenario
from .metrics import build_evaluation_metrics


SUPPORTED_BASELINES = {
    "weighted_score",
    "closest",
    "cheapest",
    "fastest",
    "overload_aware",
    "random_valid",
}


class BaselinePolicyEvaluator:
    """Evaluate deterministic recommendation baselines over fixed-seed RL scenarios.

    This first PR2 version is intentionally request-centric: it advances scenario time and
    reuses the live recommendation path, but it does not yet perform full closed-loop
    allocation rollouts for all baselines. Metrics therefore reflect feasible recommendation
    quality at decision time, which is enough to lock scenario seeds, contracts, and
    comparison plumbing before Gymnasium or training work begins.
    """

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.repository = DundeeSimulationRepository(self.repo_root)
        self.bundle = self.repository.load_bundle()
        self.random_valid_policy = RandomValidPolicy(seed="random_valid")

    def evaluate_policy(
        self,
        policy_name: str,
        scenario: RLEpisodeScenario,
        requests: list[ExternalChargingRequest],
    ) -> EvaluationMetrics:
        normalized_policy = str(policy_name).strip().lower()
        if normalized_policy not in SUPPORTED_BASELINES:
            raise ValueError(f"Unsupported RL baseline policy: {policy_name}")

        env = self._build_env(scenario)
        env.start()

        served_count = 0
        missed_count = 0
        invalid_action_count = 0
        overload_attempt_count = 0
        costs_gbp: list[float] = []
        distances_km: list[float] = []
        waits_minutes: list[float] = []
        durations_minutes: list[float] = []
        headroom_kw: list[float] = []
        decision_latency_ms: list[float] = []

        for request in sorted(requests, key=lambda item: (item.request_timestamp, item.request_id or item.client_request_id or "")):
            request_slot = floor_to_timebase(request.request_timestamp)
            while env.current_time < request_slot:
                env.current_time = env.current_time + timedelta(minutes=15)

            started = perf_counter()
            response = env.get_ranked_recommendations(
                request,
                recommendation_policy_name=None if normalized_policy == "random_valid" else normalized_policy,
            )
            options = [option for option in [response.top_recommendation, *response.alternatives] if option is not None]
            if normalized_policy == "random_valid":
                chosen = self.random_valid_policy.select_option(
                    request_id=request.request_id or request.client_request_id or f"request-{len(decision_latency_ms)}",
                    options=options,
                )
            else:
                chosen = response.top_recommendation
            decision_latency_ms.append((perf_counter() - started) * 1000.0)

            if chosen is None:
                missed_count += 1
                continue

            served_count += 1
            costs_gbp.append(float(chosen.estimated_cost_gbp))
            distances_km.append(float(chosen.distance_km))
            waits_minutes.append(float(chosen.estimated_wait_minutes))
            durations_minutes.append(float(chosen.estimated_duration_minutes))
            headroom_kw.append(float(chosen.transformer_headroom_kw))
            if float(chosen.transformer_headroom_kw) <= 0.0:
                overload_attempt_count += 1

        return build_evaluation_metrics(
            policy_name=normalized_policy,
            scenario=scenario,
            request_count=len(requests),
            served_count=served_count,
            missed_count=missed_count,
            invalid_action_count=invalid_action_count,
            overload_attempt_count=overload_attempt_count,
            costs_gbp=costs_gbp,
            distances_km=distances_km,
            waits_minutes=waits_minutes,
            durations_minutes=durations_minutes,
            headroom_kw=headroom_kw,
            decision_latency_ms=decision_latency_ms,
        )

    def _build_env(self, scenario: RLEpisodeScenario) -> DundeeEnv:
        topology_scenario: TopologyScenario | None = None
        if scenario.topology_scenario_id:
            topology_scenario = self.repository.load_topology_scenario(scenario.topology_scenario_id)
        return DundeeEnv(
            self.bundle,
            policy_mode="overload_aware",
            replay_year=scenario.start_ts.year,
            start_time=scenario.start_ts,
            runtime_mode="scenario",
            demand_multiplier=scenario.demand_multiplier,
            operational_start_time=scenario.start_ts,
            warm_start_minutes=0,
            replay_window_start=scenario.start_ts,
            replay_window_end=scenario.end_ts,
            topology_scenario=topology_scenario,
            dynamic_pricing_enabled=scenario.dynamic_pricing_enabled,
            routing_provider=self._build_routing_provider(scenario),
        )

    def _build_routing_provider(self, scenario: RLEpisodeScenario):
        name = str(scenario.routing_provider_name or "simple_distance").strip().lower()
        if name == "osmnx":
            return OSMnxRoutingProvider(graph_path=self.repo_root / "data" / "processed" / "routing" / "dundee_drive.graphml")
        return SimpleDistanceRoutingProvider()


__all__ = ["BaselinePolicyEvaluator", "SUPPORTED_BASELINES"]
