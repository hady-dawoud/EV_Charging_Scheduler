"""Dependency-light Dundee data helpers for offline RL training flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ev_core.data.repositories import DundeeDataBundle, DundeeSimulationRepository
from ev_core.generation.synthetic_live import SyntheticLiveRequestGenerator
from ev_core.rl.scenarios import RLScenarioSampler
from ev_core.vehicles.profiles import VehicleProfile, get_default_vehicle_profiles


DEFAULT_REQUEST_GENERATOR_SEED = "offline-training"


@dataclass(frozen=True)
class TrainingDataSummary:
    station_count: int
    chargepoint_count: int
    vehicle_profile_count: int


class DundeeTrainingDataAdapter:
    """Load Dundee training inputs without coupling to runtime storage or dashboards."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        repository: DundeeSimulationRepository | None = None,
        vehicle_profiles: dict[str, VehicleProfile] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.repository = repository or DundeeSimulationRepository(self.repo_root)
        self.vehicle_profiles = dict(vehicle_profiles or get_default_vehicle_profiles())
        self._bundle: DundeeDataBundle | None = None

    def load_bundle(self) -> DundeeDataBundle:
        if self._bundle is None:
            self._bundle = self.repository.load_bundle()
        return self._bundle

    def get_summary(self) -> TrainingDataSummary:
        bundle = self.load_bundle()
        return TrainingDataSummary(
            station_count=int(len(bundle.stations)),
            chargepoint_count=int(len(bundle.chargepoints)),
            vehicle_profile_count=int(len(self.vehicle_profiles)),
        )

    def build_request_generator(self, *, seed: int | str = DEFAULT_REQUEST_GENERATOR_SEED) -> SyntheticLiveRequestGenerator:
        bundle = self.load_bundle()
        return SyntheticLiveRequestGenerator(
            request_generator_params=bundle.request_generator_params,
            stations=bundle.stations.to_dict(orient="records"),
            vehicle_profiles=self.vehicle_profiles,
            seed=seed,
        )

    def build_scenario_sampler(self, *, routing_provider_name: str = "simple_distance") -> RLScenarioSampler:
        return RLScenarioSampler(
            bundle=self.load_bundle(),
            vehicle_profiles=self.vehicle_profiles,
            routing_provider_name=routing_provider_name,
        )


__all__ = [
    "DEFAULT_REQUEST_GENERATOR_SEED",
    "DundeeTrainingDataAdapter",
    "TrainingDataSummary",
]
