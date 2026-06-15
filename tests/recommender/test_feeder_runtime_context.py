from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.grid_advisory.contracts import GridAdvisoryResponse
from ev_core.recommender.feeder_runtime_context import build_feeder_runtime_context
from ev_core.rl_feeder.contracts import FeederAction


class FakeRepository:
    def __init__(self, actions: list[FeederAction], replay_rows: list[dict] | None = None) -> None:
        self._actions = actions
        self._replay_rows = replay_rows or []

    def load_actions(self) -> list[FeederAction]:
        return list(self._actions)

    def load_feature_stats(self) -> dict:
        return {}

    def load_grid_replay(self):
        return list(self._replay_rows)


class FakeGridClient:
    mode = "recorded"

    def __init__(self) -> None:
        self.proposals = []

    def batch_evaluate(self, proposals):
        self.proposals = list(proposals)
        return [
            GridAdvisoryResponse(
                advisory_available=True,
                physical_truth_level="area_pf",
                label_source_kind="area_reuse",
                evaluation_mode_used="replay",
                candidate_replay_confidence=0.58,
                model_version="fake_recorded_grid_advisory",
            )
            for _proposal in proposals
        ]


def action(
    station_id: str,
    area_id: str,
    connector_type: str = "ac",
    *,
    charger_kw: float = 22.0,
    latitude: float | None = None,
    longitude: float | None = None,
) -> FeederAction:
    return FeederAction(
        station_id=station_id,
        secondary_area_id=area_id,
        demand_point_id=f"demand-{station_id}",
        node_id=f"node-{station_id}",
        charger_kw=charger_kw,
        public_ev_capacity_kw=charger_kw,
        connector_type=connector_type,
        latitude=latitude,
        longitude=longitude,
    )


def request(*, charger_type: str = "Any", metadata: dict | None = None) -> ExternalChargingRequest:
    now = datetime(2024, 6, 10, 12, 0)
    return ExternalChargingRequest(
        client_request_id="client-1",
        request_timestamp=now,
        current_latitude=56.462,
        current_longitude=-2.9707,
        target_soc=80.0,
        current_soc=45.0,
        battery_kwh=60.0,
        requested_energy_kwh=21.0,
        preference_mode="closest",
        charger_type=charger_type,
        latest_finish_ts=now + timedelta(hours=3),
        source_type="external_live",
        request_id="request-1",
        zone_id="zone",
        metadata=metadata or {},
    )


def test_adapter_builds_observation_mask_and_station_ids_from_fake_repository() -> None:
    grid_client = FakeGridClient()
    result = build_feeder_runtime_context(
        request(metadata={"secondary_area_id": "area-a"}),
        repository=FakeRepository([action("station-a", "area-a"), action("station-b", "area-b")]),
        grid_advisory_client=grid_client,
    )

    assert result.context_available is True
    assert result.runtime_context["feeder_observation"].shape == (10 + 2 * 30,)
    assert result.runtime_context["feeder_action_mask"] == [True, False]
    assert result.runtime_context["feeder_station_ids"] == ["station-a", "station-b"]
    assert result.metadata["feeder_action_count"] == 2
    assert result.metadata["feeder_valid_action_count"] == 1
    assert result.metadata["feeder_selected_secondary_area_id"] == "area-a"
    assert result.metadata["feeder_area_strategy"] == "request_metadata"
    assert result.metadata["grid_truth_level"] == "area_pf"
    assert len(grid_client.proposals) == 1


def test_adapter_selects_replay_covered_area_deterministically() -> None:
    repository = FakeRepository(
        [action("station-a", "area-a"), action("station-b", "area-b")],
        replay_rows=[{"secondary_area_id": "area-b"}],
    )

    first = build_feeder_runtime_context(request(), repository=repository, grid_advisory_client=FakeGridClient())
    second = build_feeder_runtime_context(request(), repository=repository, grid_advisory_client=FakeGridClient())

    assert first.metadata["feeder_selected_secondary_area_id"] == "area-b"
    assert second.metadata["feeder_selected_secondary_area_id"] == "area-b"
    assert first.metadata["feeder_area_strategy"] == "deterministic_replay_covered_area"


def test_adapter_reports_zero_valid_actions_for_incompatible_charger() -> None:
    result = build_feeder_runtime_context(
        request(charger_type="dc", metadata={"secondary_area_id": "area-a"}),
        repository=FakeRepository([action("station-a", "area-a", connector_type="ac")]),
        grid_advisory_client=FakeGridClient(),
    )

    assert result.context_available is True
    assert result.runtime_context["feeder_action_mask"] == [False]
    assert result.metadata["feeder_valid_action_count"] == 0
    assert result.metadata["feeder_connector_strategy"] == "incompatible_request_charger"


def test_adapter_keeps_demo_bridge_actions_when_feeder_catalog_is_connector_unscoped(monkeypatch) -> None:
    monkeypatch.setenv("RL_SAFETY_MAPPING_MODE", "stable_ordinal_demo_bridge")

    result = build_feeder_runtime_context(
        request(charger_type="dc", metadata={"secondary_area_id": "area-a"}),
        repository=FakeRepository([action("station-a", "area-a", connector_type="ac")]),
        grid_advisory_client=FakeGridClient(),
    )

    assert result.context_available is True
    assert result.runtime_context["feeder_action_mask"] == [True]
    assert result.metadata["feeder_valid_action_count"] == 1
    assert result.metadata["feeder_connector_strategy"] == "stable_ordinal_demo_bridge_connector_unscoped"
    assert result.metadata["feeder_connector_compatible"] is True
    assert result.metadata["feeder_connector_bridge_used"] is True


def test_adapter_selects_nearest_connector_compatible_area_for_dc_request() -> None:
    grid_client = FakeGridClient()
    result = build_feeder_runtime_context(
        request(charger_type="rapid"),
        repository=FakeRepository(
            [
                action("ac-near", "area-a", connector_type="ac", latitude=56.462, longitude=-2.9707),
                action(
                    "rapid-nearby",
                    "area-b",
                    connector_type="rapid",
                    charger_kw=50.0,
                    latitude=56.463,
                    longitude=-2.9707,
                ),
            ]
        ),
        grid_advisory_client=grid_client,
    )

    assert result.context_available is True
    assert result.runtime_context["feeder_action_mask"] == [False, True]
    assert result.metadata["feeder_valid_action_count"] == 1
    assert result.metadata["feeder_connector_strategy"] == "compatible_request_charger"
    assert result.metadata["feeder_connector_compatible"] is True
    assert result.metadata["feeder_selected_secondary_area_id"] == "area-b"
    assert result.metadata["feeder_area_strategy"] == "nearest_connector_compatible_action_catalog"
    assert [proposal.station_id for proposal in grid_client.proposals] == ["rapid-nearby"]


def test_adapter_canonicalizes_spaced_dc_request_and_connector_aliases() -> None:
    result = build_feeder_runtime_context(
        request(charger_type="Ultra Rapid", metadata={"secondary_area_id": "area-a"}),
        repository=FakeRepository(
            [
                action("ac", "area-a", connector_type="ac"),
                action("dc-fast", "area-a", connector_type="dc-fast", charger_kw=22.0),
            ]
        ),
        grid_advisory_client=FakeGridClient(),
    )

    assert result.context_available is True
    assert result.runtime_context["feeder_action_mask"] == [False, True]
    assert result.metadata["feeder_valid_action_count"] == 1
    assert result.metadata["feeder_connector_strategy"] == "compatible_request_charger"


def test_adapter_reports_missing_artifacts_without_raising(tmp_path) -> None:
    result = build_feeder_runtime_context(request(), feeder_rl_data_dir=tmp_path)

    assert result.context_available is False
    assert result.runtime_context == {}
    assert "feeder_context_error" in result.metadata


def test_adapter_strict_mode_raises_for_missing_artifacts(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="feeder runtime context"):
        build_feeder_runtime_context(request(), feeder_rl_data_dir=tmp_path, strict=True)
