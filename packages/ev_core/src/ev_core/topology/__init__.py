"""Topology scenario support for Dundee simulator layouts."""

from .scenarios import (
    TopologyScenario,
    TopologyScenarioProvider,
    TransformerScenario,
    load_topology_scenario,
)
from .capacity_calibration import (
    STANDARD_CAPACITY_KW,
    TransformerCapacityInput,
    TransformerCapacityRecommendation,
    build_capacity_recommendations,
    capacity_warning_flags,
    recommend_transformer_capacity_kw,
)

__all__ = [
    "STANDARD_CAPACITY_KW",
    "TopologyScenario",
    "TopologyScenarioProvider",
    "TransformerCapacityInput",
    "TransformerCapacityRecommendation",
    "TransformerScenario",
    "build_capacity_recommendations",
    "capacity_warning_flags",
    "load_topology_scenario",
    "recommend_transformer_capacity_kw",
]
