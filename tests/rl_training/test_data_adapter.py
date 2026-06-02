from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_data_adapter_exposes_basic_dundee_counts() -> None:
    from ev_core.rl_training.data_adapter import DundeeTrainingDataAdapter

    adapter = DundeeTrainingDataAdapter(REPO_ROOT)
    summary = adapter.get_summary()

    assert summary.station_count > 0
    assert summary.chargepoint_count > 0
    assert summary.vehicle_profile_count > 0


def test_data_adapter_builds_request_generator_without_runtime_storage() -> None:
    from ev_core.rl_training.data_adapter import DundeeTrainingDataAdapter

    adapter = DundeeTrainingDataAdapter(REPO_ROOT)
    generator = adapter.build_request_generator(seed="offline-training-test")

    assert generator.seed == "offline-training-test"
