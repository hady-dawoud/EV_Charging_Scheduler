from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .deployment import _bool_from_env

RL_SAFETY_FILTER_MODES = frozenset({"penalty", "block"})
RL_SAFETY_MAPPING_MODES = frozenset(
    {"exact_only", "stable_ordinal_demo_bridge"}
)
RL_SAFETY_HYBRID_POLICIES = frozenset(
    {
        "rl_safety_closest",
        "rl_safety_cheapest",
        "rl_safety_fastest",
        "rl_safety_weighted",
        "rl_safety_preference",
    }
)
RL_SAFETY_POLICY_BY_BASE = {
    "closest": "rl_safety_closest",
    "cheapest": "rl_safety_cheapest",
    "fastest": "rl_safety_fastest",
    "weighted_score": "rl_safety_weighted",
}

KNOWN_RECOMMENDATION_POLICIES = frozenset(
    {
        'weighted_score',
        'closest',
        'cheapest',
        'fastest',
        'overload_aware',
        'rl_maskable_ppo',
        'rl_maskable_ppo_feeder',
        *RL_SAFETY_HYBRID_POLICIES,
    }
)


@dataclass(frozen=True)
class RecommendationConfig:
    policy_name: str = 'weighted_score'
    policy_name_configured: bool = False
    force_policy_name: str | None = None
    fallback_policy_name: str = 'weighted_score'
    max_alternatives: int = 3
    rl_policy_fail_closed: bool = False
    rl_feeder_checkpoint_path: Path | None = None
    feeder_data_dir: Path | None = None
    rl_safety_filter_enabled: bool = False
    rl_safety_filter_mode: str = "penalty"
    rl_safety_filter_strict: bool = False
    rl_safety_filter_penalty_weight: float = 0.25
    rl_safety_block_unsafe: bool = False
    rl_safety_mapping_mode: str = "exact_only"

    def __post_init__(self) -> None:
        if self.rl_safety_filter_mode not in RL_SAFETY_FILTER_MODES:
            raise ValueError(
                "rl_safety_filter_mode must be one of: "
                + ", ".join(sorted(RL_SAFETY_FILTER_MODES))
            )
        if self.rl_safety_mapping_mode not in RL_SAFETY_MAPPING_MODES:
            raise ValueError(
                "rl_safety_mapping_mode must be one of: "
                + ", ".join(sorted(RL_SAFETY_MAPPING_MODES))
            )
        if not 0.0 <= float(self.rl_safety_filter_penalty_weight) <= 1.0:
            raise ValueError(
                "rl_safety_filter_penalty_weight must be between 0.0 and 1.0."
            )

    @property
    def effective_env_policy_name(self) -> str:
        return self.force_policy_name or self.policy_name or "weighted_score"

    @property
    def policy_override_used(self) -> bool:
        return bool(
            self.force_policy_name
            or self.policy_name_configured
            or (self.policy_name and self.policy_name != "weighted_score")
        )


@dataclass(frozen=True)
class PolicySelection:
    requested_policy_name: str | None
    effective_policy_name: str
    policy_source: str
    preference_mode: str | None
    policy_override_used: bool
    rl_policy_fail_closed: bool
    rl_feeder_checkpoint_path: Path | None
    feeder_data_dir: Path | None
    rl_safety_filter_enabled: bool
    rl_safety_filter_mode: str
    rl_safety_filter_strict: bool
    rl_safety_filter_penalty_weight: float
    rl_safety_block_unsafe: bool
    rl_safety_mapping_mode: str

    def metadata(self) -> dict[str, object]:
        return {
            "requested_policy_name": self.requested_policy_name,
            "effective_policy_name": self.effective_policy_name,
            "policy_source": self.policy_source,
            "preference_mode": self.preference_mode,
            "policy_override_used": self.policy_override_used,
            "rl_policy_fail_closed": self.rl_policy_fail_closed,
            "rl_feeder_checkpoint_path": None if self.rl_feeder_checkpoint_path is None else self.rl_feeder_checkpoint_path.as_posix(),
            "feeder_data_dir": None if self.feeder_data_dir is None else self.feeder_data_dir.as_posix(),
            "rl_safety_filter_enabled": self.rl_safety_filter_enabled,
            "rl_safety_filter_mode": self.rl_safety_filter_mode,
            "rl_safety_filter_strict": self.rl_safety_filter_strict,
            "rl_safety_filter_penalty_weight": self.rl_safety_filter_penalty_weight,
            "rl_safety_block_unsafe": self.rl_safety_block_unsafe,
            "rl_safety_mapping_mode": self.rl_safety_mapping_mode,
        }


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _path_from_env(value: str | None) -> Path | None:
    if value is None or not value.strip():
        return None
    return Path(value.strip()).expanduser()


def is_rl_safety_policy(policy_name: str | None) -> bool:
    return str(policy_name or "") in RL_SAFETY_HYBRID_POLICIES


def _effective_safety_policy(
    policy_name: str,
    *,
    safety_enabled: bool,
) -> str:
    if is_rl_safety_policy(policy_name):
        return policy_name
    if safety_enabled:
        return RL_SAFETY_POLICY_BY_BASE.get(policy_name, policy_name)
    return policy_name


def select_recommendation_policy(
    *,
    preference_mode: str | None,
    explicit_policy_name: str | None = None,
    config: RecommendationConfig | None = None,
) -> PolicySelection:
    cfg = config or recommendation_config_from_env()
    if cfg.force_policy_name:
        requested = cfg.force_policy_name
        source = "force_recommendation_policy"
        policy_override_used = True
    elif cfg.policy_name:
        requested = cfg.policy_name
        source = "recommendation_policy_name"
        policy_override_used = cfg.policy_override_used
    elif explicit_policy_name:
        requested = explicit_policy_name
        source = "explicit_policy_parameter"
        policy_override_used = True
    else:
        requested = preference_mode or "weighted_score"
        source = "preference_mode" if preference_mode else "default"
        policy_override_used = False

    explicit_hybrid = is_rl_safety_policy(requested)
    safety_enabled = bool(cfg.rl_safety_filter_enabled or explicit_hybrid)
    effective = _effective_safety_policy(
        requested,
        safety_enabled=safety_enabled,
    )
    return PolicySelection(
        requested_policy_name=requested,
        effective_policy_name=effective,
        policy_source=source,
        preference_mode=preference_mode,
        policy_override_used=policy_override_used,
        rl_policy_fail_closed=cfg.rl_policy_fail_closed,
        rl_feeder_checkpoint_path=cfg.rl_feeder_checkpoint_path,
        feeder_data_dir=cfg.feeder_data_dir,
        rl_safety_filter_enabled=safety_enabled,
        rl_safety_filter_mode=cfg.rl_safety_filter_mode,
        rl_safety_filter_strict=cfg.rl_safety_filter_strict,
        rl_safety_filter_penalty_weight=cfg.rl_safety_filter_penalty_weight,
        rl_safety_block_unsafe=cfg.rl_safety_block_unsafe,
        rl_safety_mapping_mode=cfg.rl_safety_mapping_mode,
    )


def recommendation_config_from_env() -> RecommendationConfig:
    policy_name = _optional_env('RECOMMENDATION_POLICY_NAME')
    return RecommendationConfig(
        policy_name=policy_name or '',
        policy_name_configured=policy_name is not None,
        force_policy_name=_optional_env('FORCE_RECOMMENDATION_POLICY'),
        fallback_policy_name=os.getenv('RL_FALLBACK_POLICY_NAME', 'weighted_score'),
        rl_policy_fail_closed=_bool_from_env(os.getenv('RL_POLICY_FAIL_CLOSED'), False),
        rl_feeder_checkpoint_path=_path_from_env(os.getenv('RL_FEEDER_CHECKPOINT_PATH')),
        feeder_data_dir=_path_from_env(os.getenv('FEEDER_RL_DATA_DIR')),
        rl_safety_filter_enabled=_bool_from_env(
            os.getenv("RL_SAFETY_FILTER_ENABLED"),
            False,
        ),
        rl_safety_filter_mode=os.getenv(
            "RL_SAFETY_FILTER_MODE",
            "penalty",
        ).strip().lower(),
        rl_safety_filter_strict=_bool_from_env(
            os.getenv("RL_SAFETY_FILTER_STRICT"),
            False,
        ),
        rl_safety_filter_penalty_weight=float(
            os.getenv("RL_SAFETY_FILTER_PENALTY_WEIGHT", "0.25")
        ),
        rl_safety_block_unsafe=_bool_from_env(
            os.getenv("RL_SAFETY_BLOCK_UNSAFE"),
            False,
        ),
        rl_safety_mapping_mode=os.getenv(
            "RL_SAFETY_MAPPING_MODE",
            "exact_only",
        ).strip().lower(),
    )
