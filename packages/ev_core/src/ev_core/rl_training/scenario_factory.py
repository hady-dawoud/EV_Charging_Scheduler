"""Reproducible Dundee scenario construction for offline training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ev_core.config.training import RLTrainingConfig
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.rl.contracts import RLEpisodeScenario

from .data_adapter import DEFAULT_REQUEST_GENERATOR_SEED, DundeeTrainingDataAdapter


@dataclass(frozen=True)
class OfflineTrainingScenarioRequest:
    split: str = "train"
    seed: int = 1000
    duration_hours: int = 1
    demand_level: str = "normal"
    routing_provider_name: str = "simple_distance"
    dynamic_pricing_enabled: bool = True


@dataclass(frozen=True)
class OfflineTrainingScenarioBundle:
    scenario: RLEpisodeScenario
    requests: tuple[ExternalChargingRequest, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


class OfflineDundeeScenarioFactory:
    """Build fixed-seed offline training scenarios from repo-backed Dundee data."""

    def __init__(
        self,
        *,
        repo_root: str | Any,
        training_config: RLTrainingConfig | None = None,
        data_adapter: DundeeTrainingDataAdapter | None = None,
    ) -> None:
        self.training_config = training_config or RLTrainingConfig()
        self.data_adapter = data_adapter or DundeeTrainingDataAdapter(repo_root)

    def default_request(self) -> OfflineTrainingScenarioRequest:
        config = self.training_config
        return OfflineTrainingScenarioRequest(
            split=config.split,
            seed=config.seed,
            duration_hours=config.duration_hours,
            demand_level=config.demand_level,
            routing_provider_name=config.routing_provider_name,
            dynamic_pricing_enabled=bool(config.dynamic_pricing_enabled),
        )

    def build(self, request: OfflineTrainingScenarioRequest | None = None) -> OfflineTrainingScenarioBundle:
        resolved_request = request or self.default_request()
        sampler = self.data_adapter.build_scenario_sampler(
            routing_provider_name=resolved_request.routing_provider_name,
        )
        scenario = sampler.sample(
            seed=resolved_request.seed,
            split=resolved_request.split,
            duration_hours=resolved_request.duration_hours,
            demand_level=resolved_request.demand_level,
        )
        scenario = replace(
            scenario,
            routing_provider_name=resolved_request.routing_provider_name,
            dynamic_pricing_enabled=bool(resolved_request.dynamic_pricing_enabled),
        )
        request_generator = self.data_adapter.build_request_generator(seed=DEFAULT_REQUEST_GENERATOR_SEED)
        generated_requests = tuple(
            sampler.generate_requests_for_scenario(scenario, request_generator=request_generator)
            if hasattr(sampler, "generate_requests_for_scenario")
            else ()
        )
        if not generated_requests:
            from ev_core.rl.scenarios import generate_requests_for_scenario

            generated_requests = tuple(generate_requests_for_scenario(scenario, request_generator=request_generator))
        metadata = {
            "scenario_id": scenario.scenario_id,
            "split": scenario.split,
            "seed": scenario.seed,
            "routing_provider_name": scenario.routing_provider_name,
            "dynamic_pricing_enabled": scenario.dynamic_pricing_enabled,
            "request_count": len(generated_requests),
        }
        return OfflineTrainingScenarioBundle(
            scenario=scenario,
            requests=generated_requests,
            metadata=metadata,
        )


__all__ = [
    "OfflineDundeeScenarioFactory",
    "OfflineTrainingScenarioBundle",
    "OfflineTrainingScenarioRequest",
]
