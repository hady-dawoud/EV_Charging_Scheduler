from pathlib import Path

import pytest

from ev_core.config import path_from_env
from ev_core.config.pricing import PricingConfig, pricing_config_from_env
from ev_core.config.recommendation import RecommendationConfig, recommendation_config_from_env
from ev_core.config.routing import RoutingConfig, routing_config_from_env
from ev_core.config.topology import topology_config_from_env


def test_defaults_for_routing_recommendation_pricing() -> None:
    assert RoutingConfig().provider_name == 'simple_distance'
    assert RecommendationConfig().policy_name == 'weighted_score'
    assert PricingConfig().dynamic_pricing_enabled is True


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


def test_path_from_env() -> None:
    assert path_from_env(None) is None
    assert path_from_env('  ') is None
    assert path_from_env('models/rl') == Path('models/rl')
