from pathlib import Path

import pytest

from ev_core.config import path_from_env
from ev_core.config.pricing import PricingConfig, pricing_config_from_env
from ev_core.config.recommendation import (
    KNOWN_RECOMMENDATION_POLICIES,
    RecommendationConfig,
    recommendation_config_from_env,
)
from ev_core.config.routing import RoutingConfig, routing_config_from_env
from ev_core.config.topology import topology_config_from_env


def test_defaults_for_routing_recommendation_pricing() -> None:
    assert RoutingConfig().provider_name == 'simple_distance'
    assert RecommendationConfig().policy_name == 'weighted_score'
    assert PricingConfig().dynamic_pricing_enabled is True


def test_known_recommendation_policies_include_checkpoint_backed_hooks() -> None:
    assert 'rl_maskable_ppo' in KNOWN_RECOMMENDATION_POLICIES
    assert 'rl_maskable_ppo_feeder' in KNOWN_RECOMMENDATION_POLICIES


def test_recommendation_safety_defaults_are_conservative() -> None:
    config = RecommendationConfig()

    assert config.rl_safety_filter_enabled is False
    assert config.rl_safety_filter_mode == "penalty"
    assert config.rl_safety_filter_strict is False
    assert config.rl_safety_filter_penalty_weight == 0.25
    assert config.rl_safety_block_unsafe is False
    assert config.rl_safety_mapping_mode == "exact_only"


def test_known_policies_include_all_hybrid_names() -> None:
    assert {
        "rl_safety_closest",
        "rl_safety_cheapest",
        "rl_safety_fastest",
        "rl_safety_weighted",
        "rl_safety_preference",
    }.issubset(KNOWN_RECOMMENDATION_POLICIES)


def test_topology_defaults_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('TOPOLOGY_SCENARIO_ID', raising=False)
    assert topology_config_from_env().topology_scenario_id is None


def test_env_parsing_for_routing_pricing_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ROUTING_PROVIDER_NAME', 'osmnx')
    monkeypatch.setenv('OSMNX_GRAPH_PATH', 'data/processed/routing/dundee_drive.graphml')
    monkeypatch.setenv('OSMNX_FAIL_CLOSED', 'true')
    monkeypatch.setenv('PRICING_MODEL', 'dundee_tariff_dynamic')
    monkeypatch.setenv('DYNAMIC_PRICING_ENABLED', 'false')
    monkeypatch.setenv('RECOMMENDATION_POLICY_NAME', 'closest')

    routing = routing_config_from_env()
    pricing = pricing_config_from_env()
    recommendation = recommendation_config_from_env()

    assert routing.provider_name == 'osmnx'
    assert routing.osmnx_graph_path == Path('data/processed/routing/dundee_drive.graphml')
    assert routing.osmnx_fail_closed is True
    assert pricing.dynamic_pricing_enabled is False
    assert recommendation.policy_name == 'closest'


def test_recommendation_config_reads_force_policy_and_feeder_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('RECOMMENDATION_POLICY_NAME', 'closest')
    monkeypatch.setenv('FORCE_RECOMMENDATION_POLICY', 'rl_maskable_ppo_feeder')
    monkeypatch.setenv('RL_FEEDER_CHECKPOINT_PATH', 'models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip')
    monkeypatch.setenv('FEEDER_RL_DATA_DIR', 'data/processed/evside_feeder_rl')
    monkeypatch.setenv('RL_POLICY_FAIL_CLOSED', 'true')

    recommendation = recommendation_config_from_env()

    assert recommendation.policy_name == 'closest'
    assert recommendation.force_policy_name == 'rl_maskable_ppo_feeder'
    assert recommendation.effective_env_policy_name == 'rl_maskable_ppo_feeder'
    assert recommendation.rl_feeder_checkpoint_path == Path('models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip')
    assert recommendation.feeder_data_dir == Path('data/processed/evside_feeder_rl')
    assert recommendation.rl_policy_fail_closed is True


def test_recommendation_config_strips_whitespace_from_feeder_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "RL_FEEDER_CHECKPOINT_PATH",
        "  models/rl_feeder_final/checkpoint.zip  ",
    )
    monkeypatch.setenv(
        "FEEDER_RL_DATA_DIR",
        "  data/processed/evside_feeder_rl  ",
    )

    recommendation = recommendation_config_from_env()

    assert recommendation.rl_feeder_checkpoint_path == Path(
        "models/rl_feeder_final/checkpoint.zip"
    )
    assert recommendation.feeder_data_dir == Path(
        "data/processed/evside_feeder_rl"
    )


def test_recommendation_config_reads_rl_safety_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RL_SAFETY_FILTER_ENABLED", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_MODE", "block")
    monkeypatch.setenv("RL_SAFETY_FILTER_STRICT", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_PENALTY_WEIGHT", "0.75")
    monkeypatch.setenv("RL_SAFETY_BLOCK_UNSAFE", "true")
    monkeypatch.setenv("RL_SAFETY_MAPPING_MODE", "stable_ordinal_demo_bridge")

    config = recommendation_config_from_env()

    assert config.rl_safety_filter_enabled is True
    assert config.rl_safety_filter_mode == "block"
    assert config.rl_safety_filter_strict is True
    assert config.rl_safety_filter_penalty_weight == 0.75
    assert config.rl_safety_block_unsafe is True
    assert config.rl_safety_mapping_mode == "stable_ordinal_demo_bridge"


@pytest.mark.parametrize("value", ["unknown", "soft"])
def test_invalid_rl_safety_mode_fails(value: str) -> None:
    with pytest.raises(ValueError, match="rl_safety_filter_mode"):
        RecommendationConfig(rl_safety_filter_mode=value)


@pytest.mark.parametrize("value", ["hash_bridge", "nearest"])
def test_invalid_rl_safety_mapping_mode_fails(value: str) -> None:
    with pytest.raises(ValueError, match="rl_safety_mapping_mode"):
        RecommendationConfig(rl_safety_mapping_mode=value)


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_invalid_rl_safety_penalty_weight_fails(value: float) -> None:
    with pytest.raises(ValueError, match="rl_safety_filter_penalty_weight"):
        RecommendationConfig(rl_safety_filter_penalty_weight=value)


def test_path_from_env() -> None:
    assert path_from_env(None) is None
    assert path_from_env('  ') is None
    assert path_from_env('models/rl') == Path('models/rl')
