from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from datetime import datetime

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.vehicles.profiles import get_default_vehicle_profiles


REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _bundle():
    return DundeeSimulationRepository(REPO_ROOT).load_bundle()


def _build_request_generator() -> SyntheticLiveRequestGenerator:
    bundle = _bundle()
    return SyntheticLiveRequestGenerator(
        request_generator_params=bundle.request_generator_params,
        stations=bundle.stations.to_dict(orient="records"),
        vehicle_profiles=get_default_vehicle_profiles(),
        seed="rl-eval-test",
    )


def test_evaluation_metrics_are_json_serializable() -> None:
    from ev_core.rl.contracts import EvaluationMetrics

    metrics = EvaluationMetrics(
        policy_name="weighted_score",
        scenario_id="scenario-1",
        seed=1000,
        request_count=10,
        served_count=8,
        missed_count=2,
        invalid_action_count=0,
        overload_attempt_count=0,
        average_cost_gbp=11.2,
        average_distance_km=1.8,
        average_wait_minutes=3.0,
        average_duration_minutes=48.0,
        average_transformer_headroom_kw=120.0,
        decision_latency_ms_mean=1.5,
    )

    payload = metrics.to_dict()

    assert json.loads(json.dumps(payload))["policy_name"] == "weighted_score"


def test_forecast_feature_snapshot_defaults_to_none_source() -> None:
    from ev_core.rl.forecast_features import ForecastFeatureSnapshot

    snapshot = ForecastFeatureSnapshot()

    assert snapshot.source == "none"


def test_baseline_policy_evaluator_supports_weighted_score_smoke_path() -> None:
    from ev_core.rl.evaluation import BaselinePolicyEvaluator
    from ev_core.rl.scenarios import RLScenarioSampler, generate_requests_for_scenario

    sampler = RLScenarioSampler(bundle=_bundle())
    scenario = sampler.sample(seed=1008, duration_hours=1, demand_level="normal")
    requests = generate_requests_for_scenario(
        scenario,
        request_generator=_build_request_generator(),
    )[:5]

    evaluator = BaselinePolicyEvaluator(repo_root=REPO_ROOT)
    metrics = evaluator.evaluate_policy("weighted_score", scenario, requests)

    assert metrics.policy_name == "weighted_score"
    assert metrics.scenario_id == scenario.scenario_id
    assert metrics.request_count == len(requests)
    assert metrics.served_count + metrics.missed_count == len(requests)
