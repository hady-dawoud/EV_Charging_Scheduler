"""Verify fixed-seed RL scenario sampling and lightweight baseline evaluation."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.rl.evaluation import BaselinePolicyEvaluator
from ev_core.rl.scenarios import RLScenarioSampler, generate_requests_for_scenario
from ev_core.vehicles.profiles import get_default_vehicle_profiles


def main() -> int:
    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    sampler = RLScenarioSampler(bundle=bundle)
    request_generator = SyntheticLiveRequestGenerator(
        request_generator_params=bundle.request_generator_params,
        stations=bundle.stations.to_dict(orient="records"),
        vehicle_profiles=get_default_vehicle_profiles(),
        seed="verify-rl-sampler",
    )
    evaluator = BaselinePolicyEvaluator(repo_root=REPO_ROOT)

    scenarios = [
        sampler.sample(seed=1000, duration_hours=1, demand_level="normal"),
        sampler.sample(seed=2000, duration_hours=3, demand_level="busy"),
        sampler.sample(seed=3000, duration_hours=6, demand_level="stress"),
    ]

    print("RL scenario sampler verification")
    for scenario in scenarios:
        print(f"scenario_id: {scenario.scenario_id}")
        print(f"split: {scenario.split}")
        print(f"seed: {scenario.seed}")
        print(f"duration_hours: {scenario.duration_hours}")
        print(f"demand_level: {scenario.demand_level}")
        print(f"demand_multiplier: {scenario.demand_multiplier}")
        print(f"request_count: {scenario.request_count}")

    requests = generate_requests_for_scenario(scenarios[0], request_generator=request_generator)
    first_request = requests[0]
    print(f"first_request_id: {first_request.request_id}")
    print(f"first_request_metadata: {first_request.metadata}")

    metrics = evaluator.evaluate_policy("weighted_score", scenarios[0], requests[:5])
    print(f"baseline_policy: {metrics.policy_name}")
    print(f"served_count: {metrics.served_count}")
    print(f"missed_count: {metrics.missed_count}")
    print(f"average_cost_gbp: {metrics.average_cost_gbp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
