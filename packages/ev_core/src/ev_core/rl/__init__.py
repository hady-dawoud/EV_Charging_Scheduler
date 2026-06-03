"""RL-preparation contracts, samplers, and evaluation helpers."""

from .action_mask import build_station_action_mask
from .baselines import RandomValidPolicy
from .contracts import EvaluationMetrics, RLEpisodeScenario, ScenarioSeedSplit
from .evaluation import BaselinePolicyEvaluator
from .forecast_features import ForecastFeatureSnapshot
from .observations import ObservationBuilder, ObservationSpec
from .rewards import RewardBreakdown, StationSelectionReward
from .scenarios import RLScenarioSampler, generate_requests_for_scenario

try:
    from .env import DundeeStationSelectionEnv
except ImportError:  # Gymnasium is optional for non-env code paths.
    DundeeStationSelectionEnv = None

__all__ = [
    "BaselinePolicyEvaluator",
    "build_station_action_mask",
    "DundeeStationSelectionEnv",
    "EvaluationMetrics",
    "ForecastFeatureSnapshot",
    "ObservationBuilder",
    "ObservationSpec",
    "RLEpisodeScenario",
    "RLScenarioSampler",
    "RandomValidPolicy",
    "RewardBreakdown",
    "ScenarioSeedSplit",
    "StationSelectionReward",
    "generate_requests_for_scenario",
]
