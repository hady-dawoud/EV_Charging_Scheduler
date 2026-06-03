from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TopologyConfig:
    topology_scenario_id: str | None = None


def topology_config_from_env() -> TopologyConfig:
    return TopologyConfig(topology_scenario_id=os.getenv('TOPOLOGY_SCENARIO_ID') or None)
