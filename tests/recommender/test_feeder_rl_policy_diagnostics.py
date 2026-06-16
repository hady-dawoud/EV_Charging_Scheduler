from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ev_core.recommender.feeder_rl_policy import (
    FeederActionPrediction,
    FeederMaskablePPORuntimePolicy,
)
from ev_core.recommender.ranker import CandidateContext, RecommendationInput


def candidate(station_id: str, *, distance_km: float = 1.0) -> CandidateContext:
    return CandidateContext(
        station_id=station_id,
        station_name=f"Station {station_id}",
        zone_id="zone",
        transformer_id="tx",
        distance_km=distance_km,
        estimated_wait_minutes=0,
        estimated_duration_minutes=30,
        estimated_cost_gbp=5.0,
        transformer_headroom_kw=200.0,
        current_queue=0,
        utilization=0.1,
        charger_compatible=True,
    )


def request(candidates) -> RecommendationInput:
    return RecommendationInput(
        request_id="request-1",
        preference_mode="closest",
        candidates=tuple(candidates),
    )


class FakeModel:
    def __init__(self, action_index: int = 1, expected_shape: int = 4) -> None:
        self.action_index = action_index
        self.observation_space = SimpleNamespace(shape=(expected_shape,))
        self.seen_observation = None
        self.seen_action_masks = None

    def predict(self, observation, *, deterministic: bool, action_masks):
        self.seen_observation = observation
        self.seen_action_masks = action_masks
        return np.asarray([self.action_index]), None


class FailingModel(FakeModel):
    def predict(self, observation, *, deterministic: bool, action_masks):
        raise RuntimeError("synthetic prediction failure")


class EmptyActionModel(FakeModel):
    def predict(self, observation, *, deterministic: bool, action_masks):
        return np.asarray([]), None


class InvalidMaskValue:
    def __bool__(self) -> bool:
        raise RuntimeError("synthetic mask failure")


def complete_runtime_context() -> dict[str, object]:
    return {
        "feeder_observation": np.zeros(4, dtype=np.float32),
        "feeder_action_mask": [False, True],
        "feeder_station_ids": ["feeder-a", "feeder-b"],
    }


def test_predict_feeder_action_returns_validated_action_metadata(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    model = FakeModel(action_index=1, expected_shape=4)
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: model)

    prediction = policy.predict_feeder_action(complete_runtime_context())

    assert isinstance(prediction, FeederActionPrediction)
    assert prediction.available is True
    assert prediction.action_index == 1
    assert prediction.station_id == "feeder-b"
    assert prediction.fallback_used is False
    assert prediction.error is None
    assert model.seen_observation.shape == (4,)
    assert model.seen_action_masks.tolist() == [False, True]
    with pytest.raises(FrozenInstanceError):
        prediction.available = False


def test_predict_feeder_action_returns_controlled_error_without_fallback() -> None:
    policy = FeederMaskablePPORuntimePolicy(
        checkpoint_path=Path("missing-checkpoint.zip")
    )

    prediction = policy.predict_feeder_action({})

    assert prediction.available is False
    assert prediction.action_index is None
    assert prediction.station_id is None
    assert prediction.fallback_used is True
    assert prediction.error == "checkpoint_missing"


def test_predict_feeder_action_validates_observation_shape(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(
        policy,
        "_load_model",
        lambda: FakeModel(action_index=1, expected_shape=5),
    )

    prediction = policy.predict_feeder_action(complete_runtime_context())

    assert prediction.available is False
    assert prediction.error == "feeder_observation_shape_mismatch"


def test_predict_feeder_action_validates_action_mask_length(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FakeModel())
    context = complete_runtime_context()
    context["feeder_action_mask"] = [True]

    prediction = policy.predict_feeder_action(context)

    assert prediction.available is False
    assert prediction.error == "feeder_mask_station_length_mismatch"


def test_predict_feeder_action_requires_station_ids(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FakeModel())
    context = complete_runtime_context()
    context["feeder_station_ids"] = []

    prediction = policy.predict_feeder_action(context)

    assert prediction.available is False
    assert prediction.error == "feeder_station_ids_missing"


def test_predict_feeder_action_treats_none_station_ids_as_missing(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FakeModel())
    context = complete_runtime_context()
    context["feeder_station_ids"] = None

    prediction = policy.predict_feeder_action(context)

    assert prediction.available is False
    assert prediction.error == "feeder_station_ids_missing"


def test_predict_feeder_action_returns_controlled_invalid_mask_error(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FakeModel())
    context = complete_runtime_context()
    context["feeder_action_mask"] = [InvalidMaskValue(), True]

    prediction = policy.predict_feeder_action(context)

    assert prediction.available is False
    assert prediction.error == (
        "feeder_action_mask_invalid: synthetic mask failure"
    )


def test_predict_feeder_action_rejects_out_of_range_action(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(
        policy,
        "_load_model",
        lambda: FakeModel(action_index=2, expected_shape=4),
    )

    prediction = policy.predict_feeder_action(complete_runtime_context())

    assert prediction.available is False
    assert prediction.error == "predicted_action_out_of_range"


def test_predict_feeder_action_rejects_masked_action(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(
        policy,
        "_load_model",
        lambda: FakeModel(action_index=0, expected_shape=4),
    )

    prediction = policy.predict_feeder_action(complete_runtime_context())

    assert prediction.available is False
    assert prediction.error == "predicted_action_masked_out"


def test_predict_feeder_action_returns_controlled_prediction_error(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FailingModel())

    prediction = policy.predict_feeder_action(complete_runtime_context())

    assert prediction.available is False
    assert prediction.action_index is None
    assert prediction.station_id is None
    assert prediction.fallback_used is True
    assert prediction.error == "prediction_failed: synthetic prediction failure"


def test_predict_feeder_action_returns_controlled_invalid_action_error(
    monkeypatch,
    tmp_path,
) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: EmptyActionModel())

    prediction = policy.predict_feeder_action(complete_runtime_context())

    assert prediction.available is False
    assert prediction.action_index is None
    assert prediction.station_id is None
    assert prediction.fallback_used is True
    assert prediction.error.startswith("predicted_action_invalid:")


def test_feeder_policy_reports_missing_dependency_or_checkpoint_without_importing_sb3(monkeypatch) -> None:
    monkeypatch.delenv("RL_POLICY_FAIL_CLOSED", raising=False)
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=Path("missing-checkpoint.zip"))
    candidates = [candidate("dundee-a")]

    result = policy.rank(request(candidates), candidates, runtime_context={})

    assert result
    assert result[0].metadata["policy_name"] == "rl_maskable_ppo_feeder"
    assert result[0].metadata["fallback_used"] is True
    assert result[0].metadata["fallback_reason"] == "checkpoint_missing"


def test_feeder_policy_fail_closed_returns_no_options_for_missing_context(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("RL_POLICY_FAIL_CLOSED", "true")
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    fake_model = FakeModel()
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: fake_model)
    candidates = [candidate("dundee-a")]

    result = policy.rank(request(candidates), candidates, runtime_context={})

    assert result == []


def test_feeder_policy_validates_missing_observation_with_controlled_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RL_POLICY_FAIL_CLOSED", raising=False)
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FakeModel())
    candidates = [candidate("dundee-a")]

    result = policy.rank(
        request(candidates),
        candidates,
        runtime_context={
            "feeder_action_mask": [True, False],
            "feeder_station_ids": ["feeder-a", "feeder-b"],
        },
    )

    assert result[0].metadata["fallback_used"] is True
    assert result[0].metadata["fallback_reason"] == "feeder_observation_missing"


def test_feeder_policy_validates_mask_station_length_mismatch(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RL_POLICY_FAIL_CLOSED", raising=False)
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: FakeModel(expected_shape=2))
    candidates = [candidate("dundee-a")]

    result = policy.rank(
        request(candidates),
        candidates,
        runtime_context={
            "feeder_observation": np.zeros(2, dtype=np.float32),
            "feeder_action_mask": [True],
            "feeder_station_ids": ["feeder-a", "feeder-b"],
        },
    )

    assert result[0].metadata["fallback_reason"] == "feeder_mask_station_length_mismatch"


def test_feeder_policy_maps_predicted_action_to_feeder_station_and_masks(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RL_POLICY_FAIL_CLOSED", raising=False)
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    fake_model = FakeModel(action_index=1, expected_shape=4)
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: fake_model)
    candidates = [candidate("dundee-a", distance_km=3.0), candidate("dundee-b", distance_km=1.0)]

    result = policy.rank(
        request(candidates),
        candidates,
        runtime_context={
            "feeder_observation": np.zeros(4, dtype=np.float32),
            "feeder_action_mask": [False, True, True],
            "feeder_station_ids": ["feeder-a", "feeder-b", "feeder-c"],
            "feeder_data_dir": "data/processed/evside_feeder_rl",
            "grid_advisory_mode": "recorded",
            "grid_truth_level": "area_pf",
            "grid_label_source_kind": "area_reuse",
        },
    )

    assert result
    assert fake_model.seen_action_masks.dtype == bool
    assert fake_model.seen_action_masks.shape == (3,)
    assert result[0].metadata["fallback_used"] is False
    assert result[0].metadata["feeder_selected_action_index"] == 1
    assert result[0].metadata["feeder_selected_station_id"] == "feeder-b"
    assert result[0].metadata["feeder_station_candidate_match"] is False
    assert result[0].metadata["offline_feeder_rl_adapter"] is True
