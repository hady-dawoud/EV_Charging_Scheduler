from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from ev_core.recommender.ranker import CandidateContext, RecommendationInput


def _candidate(station_id: str, *, distance_km: float) -> CandidateContext:
    return CandidateContext(
        station_id=station_id,
        station_name=station_id,
        zone_id="zone",
        transformer_id="tx",
        distance_km=distance_km,
        estimated_wait_minutes=0,
        estimated_duration_minutes=30,
        estimated_cost_gbp=5.0 + distance_km,
        transformer_headroom_kw=200.0,
        current_queue=0,
        utilization=0.1,
        charger_compatible=True,
        metadata={"effective_power_kw": 22.0},
    )


def test_policy_registry_returns_rl_maskable_ppo_policy() -> None:
    from ev_core.recommender.policy_registry import PolicyRegistry

    assert PolicyRegistry().get("rl_maskable_ppo").name == "rl_maskable_ppo"


def test_rl_policy_falls_back_when_checkpoint_is_missing(monkeypatch, tmp_path) -> None:
    from ev_core.recommender.rl_policy import MaskablePPORuntimePolicy

    monkeypatch.setenv("RL_POLICY_CHECKPOINT_PATH", str(tmp_path / "missing.zip"))
    monkeypatch.setenv("GRID_ADVISORY_MODE", "disabled")
    candidates = [_candidate("near", distance_km=0.1), _candidate("far", distance_km=4.0)]
    request = RecommendationInput(request_id="request-1", preference_mode="closest", candidates=tuple(candidates))
    now = datetime(2024, 1, 1, 12, 0)
    simulation_request = SimpleNamespace(
        request_id="request-1",
        client_request_id="client-1",
        arrival_ts=now,
        latest_finish_ts=now + timedelta(hours=2),
        requested_energy_kwh=24.0,
        charger_type_preference="Any",
        current_soc=20.0,
        target_soc=80.0,
        battery_kwh=60.0,
        vehicle_max_ac_kw=11.0,
        vehicle_max_dc_kw=120.0,
        metadata={},
    )

    ranked = MaskablePPORuntimePolicy().rank(
        request,
        candidates,
        runtime_context={
            "simulation_request": simulation_request,
            "station_ids": ["near", "far"],
            "simulated_timestamp": now,
        },
    )

    assert ranked[0].station_id == "near"
