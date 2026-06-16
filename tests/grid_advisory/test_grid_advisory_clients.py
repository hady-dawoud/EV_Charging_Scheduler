from __future__ import annotations

from datetime import datetime

import pandas as pd

from ev_core.grid_advisory.client import (
    DisabledGridAdvisoryClient,
    HttpGridAdvisoryClient,
    RecordedGridAdvisoryClient,
    RuntimeHttpGridAdvisoryClient,
    build_grid_advisory_client,
)
from ev_core.grid_advisory.contracts import GridSchedulePoint, GridScheduleProposal


def _proposal() -> GridScheduleProposal:
    return GridScheduleProposal(
        request_id="request-1",
        episode_id="episode-1",
        station_id="station-a",
        area_id="area-a",
        start_timestamp=datetime(2024, 1, 1, 12, 0),
        timebase_minutes=30,
        duration_steps=2,
        requested_energy_kwh=24.0,
        charger_kw=22.0,
        ev_schedule=[GridSchedulePoint(time_index=0, p_kw=22.0)],
    )


def test_disabled_grid_advisory_client_returns_neutral_response() -> None:
    response = DisabledGridAdvisoryClient().evaluate(_proposal())

    assert response.verdict == "OK"
    assert response.risk_class == "SAFE"
    assert response.advisory_available is False


def test_recorded_grid_advisory_client_reads_csv_replay(tmp_path) -> None:
    pd.DataFrame(
        [
            {
                "request_id": "request-1",
                "station_id": "station-a",
                "verdict": "REJECT",
                "risk_class": "VIOLATION",
                "v_min_pu": 0.92,
                "max_line_loading_percent": 105.0,
                "max_trafo_loading_percent": 101.0,
                "stress_score": 0.91,
                "max_allowed_kw": 7.0,
                "ood_flag": False,
                "uq_flag": True,
                "reason_codes": '["test_violation"]',
                "model_version": "recorded_test",
            }
        ]
    ).to_csv(tmp_path / "rl_candidate_advisory.csv", index=False)

    response = RecordedGridAdvisoryClient(tmp_path).evaluate(_proposal())

    assert response.verdict == "REJECT"
    assert response.risk_class == "VIOLATION"
    assert response.reason_codes == ["test_violation"]
    assert response.advisory_available is True


def test_http_grid_advisory_client_falls_back_when_unavailable(monkeypatch) -> None:
    client = HttpGridAdvisoryClient(base_url="http://127.0.0.1:1", timeout_seconds=0.1)
    monkeypatch.setattr(client, "_post_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("down")))

    response = client.evaluate(_proposal())

    assert response.verdict == "OK"
    assert response.advisory_available is False
    assert "grid_http_unavailable" in response.reason_codes


def test_runtime_http_grid_advisory_client_maps_48_step_contract(monkeypatch) -> None:
    client = RuntimeHttpGridAdvisoryClient(base_url="http://runtime.test", timeout_seconds=0.1)

    def fake_post(path, payload):
        assert path == "/v1/proposals/evaluate"
        assert payload["schema_version"] == "grid_ev_advisory.v1"
        assert payload["snapshot_id"] == "demo-snapshot-48"
        assert len(payload["submitted_schedule"]) == 48
        return {
            "schema_version": "grid_ev_advisory.v1",
            "proposal_id": payload["proposal_id"],
            "audit_id": "audit-runtime-test",
            "verdict": "REJECT",
            "model_status": "checkpoint_unaccepted",
            "reason_codes": ["predicted_thermal_violation"],
            "predictions": {
                "v_min_pu": [0.941] * 48,
                "v_max_pu": [1.01] * 48,
                "worst_edge_loading_percent": [101.0] * 48,
                "worst_trafo_loading_percent": [98.0] * 48,
                "stress_score": [0.86] * 48,
                "binding_node_ids_by_time": [[] for _ in range(48)],
                "binding_edge_ids_by_time": [["edge-1"] for _ in range(48)],
            },
            "gates": {
                "uq": {"name": "uq", "status": "pass", "reason_codes": [], "details": {}},
                "ood": {"name": "ood", "status": "pass", "reason_codes": [], "details": {}},
                "physics": {
                    "name": "physics",
                    "status": "fail",
                    "reason_codes": ["predicted_thermal_violation"],
                    "details": {},
                },
                "policy": {
                    "name": "policy",
                    "status": "fail",
                    "reason_codes": ["predicted_thermal_violation"],
                    "details": {},
                },
            },
            "counter_offer": {
                "recommended_max_ev_kw_by_time": [7.0] * 48,
                "shift_suggestions": [],
                "original_kwh": 24.0,
                "served_kwh": 14.0,
                "deferred_kwh": 4.0,
                "curtailed_kwh": 6.0,
                "served_fraction": 0.75,
                "binding_constraints": ["edge_thermal_limit"],
                "energy_conservation_passed": True,
                "gate_agreement": False,
                "counter_offer_status": "rule_based",
                "reason_codes": ["counter_offer_requires_reevaluation"],
            },
            "provenance": {
                "schema_version": "grid_ev_advisory.v1",
                "model_id": "runtime-model",
                "model_status": "checkpoint_unaccepted",
                "data_manifest_id": "demo_fixture_snapshot_v1",
                "feature_schema_hash": "schema",
                "snapshot_id": "demo-snapshot-48",
                "adapter_kind": "temporal_checkpoint",
                "calibration_version": "none",
            },
            "created_at": "2026-06-06T00:00:00Z",
            "latency_ms": 8.1,
        }

    monkeypatch.setattr(client, "_post_json", fake_post)

    response = client.evaluate(_proposal())

    assert response.verdict == "REJECT"
    assert response.max_allowed_kw == 7.0
    assert response.feasible_energy_kwh == 18.0
    assert response.bottleneck_element_type == "line"
    assert response.source_snapshot_id == "demo-snapshot-48"
    assert response.model_version == "runtime-model"


def test_build_grid_advisory_client_supports_runtime_http_mode() -> None:
    client = build_grid_advisory_client(mode="runtime_http", base_url="http://runtime.test")

    assert isinstance(client, RuntimeHttpGridAdvisoryClient)
