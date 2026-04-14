"""Feature-building placeholders for forecasting and simulation inputs."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class FeatureBuilderSpec:
    """Describes a named feature set generated on a 15-minute grid."""

    name: str
    input_tables: tuple[str, ...] = field(default_factory=tuple)
    resolution_minutes: int = 15


def build_features(frame: pd.DataFrame, spec: FeatureBuilderSpec) -> pd.DataFrame:
    """Build derived features after the project feature contract is defined."""

    raise NotImplementedError("TODO: implement feature engineering pipelines.")
