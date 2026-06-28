from __future__ import annotations

import sys

import numpy as np
import pytest

from ev_core.config.recommendation import RecommendationConfig
from ev_core.recommender.baseline_policies import (
    CheapestPolicy,
    ClosestPolicy,
    FastestPolicy,
    WeightedScorePolicy,
)
from ev_core.recommender.feeder_rl_policy import FeederActionPrediction
from ev_core.recommender.ranker import CandidateContext, RecommendationInput
from ev_core.recommender.rl_safety_filter import (
    RLSafetyCheapestPolicy,
    RLSafetyClosestPolicy,
    RLSafetyFastestPolicy,
    RLSafetyFilterConfig,
    RLSafetyPreferencePolicy,
    RLSafetyWeightedPolicy,
    safety_config_from_recommendation,
)


class FakeFeederPolicy:
    def __init__(self, prediction: FeederActionPrediction) -> None:
        self.prediction = prediction
        self.seen_runtime_context = None

    def predict_feeder_action(
        self,
        runtime_context: dict[str, object],
    ) -> FeederActionPrediction:
        self.seen_runtime_context = runtime_context
        return self.prediction


def request(preference_mode: str) -> RecommendationInput:
    candidate_values = candidates()
    return RecommendationInput(
        request_id="request-1",
        preference_mode=preference_mode,
        candidates=tuple(candidate_values),
    )


def candidates() -> list[CandidateContext]:
    return [
        CandidateContext(
            station_id="near",
            station_name="Nearest",
            zone_id="zone",
            transformer_id="tx-near",
            distance_km=0.1,
            estimated_wait_minutes=300,
            estimated_duration_minutes=300,
            estimated_cost_gbp=100.0,
            transformer_headroom_kw=0.0,
            current_queue=8,
            utilization=0.95,
            charger_compatible=True,
            metadata={
                "final_price_per_kwh": 0.80,
                "dynamic_pricing_enabled": True,
            },
        ),
        CandidateContext(
            station_id="cheap",
            station_name="Cheapest",
            zone_id="zone",
            transformer_id="tx-cheap",
            distance_km=10.0,
            estimated_wait_minutes=300,
            estimated_duration_minutes=300,
            estimated_cost_gbp=0.5,
            transformer_headroom_kw=0.0,
            current_queue=8,
            utilization=0.95,
            charger_compatible=True,
            metadata={
                "final_price_per_kwh": 0.31,
                "dynamic_pricing_enabled": True,
            },
        ),
        CandidateContext(
            station_id="fast",
            station_name="Fastest",
            zone_id="zone",
            transformer_id="tx-fast",
            distance_km=10.0,
            estimated_wait_minutes=0,
            estimated_duration_minutes=1,
            estimated_cost_gbp=100.0,
            transformer_headroom_kw=0.0,
            current_queue=0,
            utilization=0.1,
            charger_compatible=True,
            metadata={
                "final_price_per_kwh": 0.80,
                "dynamic_pricing_enabled": True,
            },
        ),
        CandidateContext(
            station_id="balanced",
            station_name="Balanced",
            zone_id="zone",
            transformer_id="tx-balanced",
            distance_km=2.0,
            estimated_wait_minutes=10,
            estimated_duration_minutes=30,
            estimated_cost_gbp=5.0,
            transformer_headroom_kw=500.0,
            current_queue=1,
            utilization=0.2,
            charger_compatible=True,
            metadata={
                "final_price_per_kwh": 0.42,
                "dynamic_pricing_enabled": True,
            },
        ),
    ]


SAFETY_METADATA_KEYS = {
    "base_preference_score",
    "rl_safety_filter_enabled",
    "rl_safety_filter_mode",
    "rl_safety_status",
    "rl_safety_score",
    "rl_safety_penalty",
    "rl_safety_penalty_weight",
    "rl_safety_adjusted_score",
    "rl_safety_blocked",
    "rl_safety_reason",
    "rl_safety_mapping_kind",
    "rl_safety_mapping_physical_claim",
    "rl_safety_mapping_warning",
    "rl_mapped_feeder_station_id",
    "rl_mapped_feeder_action_index",
    "rl_selected_feeder_station_id",
    "rl_selected_action_index",
    "feeder_selected_secondary_area_id",
    "feeder_area_strategy",
    "feeder_valid_action_count",
    "grid_truth_level",
    "grid_label_source_kind",
    "offline_feeder_rl_adapter",
    "fallback_used",
}


RAW_OPTION_FIELDS = (
    "station_id",
    "distance_km",
    "estimated_cost_gbp",
    "estimated_duration_minutes",
    "estimated_wait_minutes",
    "current_queue",
    "utilization",
    "transformer_headroom_kw",
    "charger_compatible",
)


def complete_context(**overrides: object) -> dict[str, object]:
    station_ids = [candidate.station_id for candidate in candidates()]
    context: dict[str, object] = {
        "feeder_observation": np.zeros(4, dtype=np.float32),
        "feeder_action_mask": [True] * len(station_ids),
        "feeder_station_ids": station_ids,
        "grid_advisories": {
            station_id: {
                "stress_score": 0.0,
                "opf_feasible": True,
                "verdict": "ACCEPT",
                "risk_class": "SAFE",
            }
            for station_id in station_ids
        },
        "feeder_selected_secondary_area_id": "area-a",
        "feeder_area_strategy": "test",
        "feeder_valid_action_count": len(station_ids),
        "grid_truth_level": "recorded",
        "grid_label_source_kind": "recorded_replay",
    }
    context.update(overrides)
    return context


def zero_safety_inference() -> FakeFeederPolicy:
    return FakeFeederPolicy(
        FeederActionPrediction(
            available=True,
            action_index=0,
            station_id="near",
            fallback_used=False,
            error=None,
        )
    )


def unavailable_inference(reason: str) -> FakeFeederPolicy:
    return FakeFeederPolicy(
        FeederActionPrediction(
            available=False,
            action_index=None,
            station_id=None,
            fallback_used=True,
            error=reason,
        )
    )


def safety_config(**overrides: object) -> RLSafetyFilterConfig:
    values = {
        "enabled": True,
        "mode": "penalty",
        "strict": False,
        "penalty_weight": 0.25,
        "block_unsafe": False,
        "mapping_mode": "exact_only",
        "fail_closed": False,
    }
    values.update(overrides)
    return RLSafetyFilterConfig(**values)


def build_hybrid_policy_for_test(
    hybrid_name: str,
    feeder_policy: FakeFeederPolicy,
    *,
    config: RLSafetyFilterConfig | None = None,
):
    policy_types = {
        "rl_safety_closest": RLSafetyClosestPolicy,
        "rl_safety_cheapest": RLSafetyCheapestPolicy,
        "rl_safety_fastest": RLSafetyFastestPolicy,
        "rl_safety_weighted": RLSafetyWeightedPolicy,
        "rl_safety_preference": RLSafetyPreferencePolicy,
    }
    return policy_types[hybrid_name](
        config=config or safety_config(),
        feeder_policy=feeder_policy,
    )


@pytest.mark.parametrize(
    ("hybrid_name", "preference_mode", "expected_final_ranker"),
    [
        ("rl_safety_closest", "cheapest", "closest"),
        ("rl_safety_cheapest", "closest", "cheapest"),
        ("rl_safety_fastest", "closest", "fastest"),
        ("rl_safety_weighted", "closest", "weighted_score"),
        ("rl_safety_preference", "closest", "closest"),
        ("rl_safety_preference", "cheapest", "cheapest"),
        ("rl_safety_preference", "fastest", "fastest"),
    ],
)
def test_hybrid_policy_uses_expected_wrapped_ranker(
    hybrid_name: str,
    preference_mode: str,
    expected_final_ranker: str,
) -> None:
    policy = build_hybrid_policy_for_test(
        hybrid_name,
        zero_safety_inference(),
    )

    result = policy.rank(
        request(preference_mode),
        candidates(),
        runtime_context=complete_context(),
    )

    assert policy.last_diagnostics["final_ranker"] == expected_final_ranker
    assert result[0].metadata["final_ranker"] == expected_final_ranker


@pytest.mark.parametrize(
    ("hybrid_name", "base"),
    [
        ("rl_safety_closest", ClosestPolicy()),
        ("rl_safety_cheapest", CheapestPolicy()),
        ("rl_safety_fastest", FastestPolicy()),
        ("rl_safety_weighted", WeightedScorePolicy()),
    ],
)
def test_zero_safety_preserves_wrapped_policy_order(
    hybrid_name,
    base,
) -> None:
    request_value = request("closest")
    candidate_values = candidates()
    base_ids = [
        item.station_id
        for item in base.rank(request_value, candidate_values)
    ]
    hybrid_policy = build_hybrid_policy_for_test(
        hybrid_name,
        zero_safety_inference(),
    )

    hybrid_ids = [
        item.station_id
        for item in hybrid_policy.rank(
            request_value,
            candidate_values,
            runtime_context=complete_context(),
        )
    ]

    assert hybrid_ids == base_ids


def test_explicit_hybrid_rankers_remain_distinct() -> None:
    request_value = request("closest")
    candidate_values = candidates()
    top_ids = {
        hybrid_name: build_hybrid_policy_for_test(
            hybrid_name,
            zero_safety_inference(),
        )
        .rank(
            request_value,
            candidate_values,
            runtime_context=complete_context(),
        )[0]
        .station_id
        for hybrid_name in (
            "rl_safety_closest",
            "rl_safety_cheapest",
            "rl_safety_fastest",
            "rl_safety_weighted",
        )
    }

    assert top_ids == {
        "rl_safety_closest": "near",
        "rl_safety_cheapest": "cheap",
        "rl_safety_fastest": "fast",
        "rl_safety_weighted": "balanced",
    }


def test_cheapest_uses_dynamic_estimated_cost_as_base_score() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_cheapest",
        zero_safety_inference(),
    )

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )

    cheap_option = next(item for item in result if item.station_id == "cheap")
    assert cheap_option.metadata["base_preference_score"] == pytest.approx(
        1.0 / (1.0 + cheap_option.estimated_cost_gbp),
        abs=1e-4,
    )
    assert cheap_option.metadata["final_price_per_kwh"] == 0.31
    assert cheap_option.metadata["dynamic_pricing_enabled"] is True


def test_safety_config_adapter_preserves_recommendation_settings() -> None:
    config = safety_config_from_recommendation(
        RecommendationConfig(
            rl_safety_filter_enabled=False,
            rl_safety_filter_mode="block",
            rl_safety_filter_strict=True,
            rl_safety_filter_penalty_weight=0.75,
            rl_safety_block_unsafe=True,
            rl_safety_mapping_mode="stable_ordinal_demo_bridge",
        ),
        explicit_hybrid=True,
    )

    assert config == RLSafetyFilterConfig(
        enabled=True,
        mode="block",
        strict=True,
        penalty_weight=0.75,
        block_unsafe=True,
        mapping_mode="stable_ordinal_demo_bridge",
        fail_closed=True,
    )


def test_fake_feeder_path_does_not_require_optional_ml_modules(
    monkeypatch,
) -> None:
    monkeypatch.setitem(sys.modules, "torch", None)
    monkeypatch.setitem(sys.modules, "stable_baselines3", None)
    monkeypatch.setitem(sys.modules, "sb3_contrib", None)
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
    )

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )

    assert result
    assert result[0].metadata["base_preference_score"] == result[0].score


def test_missing_prediction_fail_open_restores_deterministic_ranking() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        unavailable_inference("checkpoint_missing"),
        config=safety_config(fail_closed=False),
    )
    base = ClosestPolicy().rank(request("closest"), candidates())

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )

    assert [item.station_id for item in result] == [
        item.station_id for item in base
    ]
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is True
    assert policy.last_diagnostics["rl_safety_filter_reason"] == (
        "checkpoint_missing"
    )
    assert all(item.metadata["fallback_used"] is True for item in result)
    assert all(
        item.metadata["rl_safety_adjusted_score"]
        == item.metadata["base_preference_score"]
        for item in result
    )
    assert [
        {field: getattr(item, field) for field in RAW_OPTION_FIELDS}
        for item in result
    ] == [
        {field: getattr(item, field) for field in RAW_OPTION_FIELDS}
        for item in base
    ]


def test_missing_prediction_fail_closed_returns_empty() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        unavailable_inference("checkpoint_missing"),
        config=safety_config(fail_closed=True),
    )

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )

    assert result == []
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is False
    assert policy.last_diagnostics["rl_safety_filter_reason"] == (
        "checkpoint_missing"
    )


def test_missing_context_fail_open_restores_deterministic_ranking() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(fail_closed=False),
    )
    base = ClosestPolicy().rank(request("closest"), candidates())

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context={},
    )

    assert [item.station_id for item in result] == [
        item.station_id for item in base
    ]
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is True
    assert policy.last_diagnostics["rl_safety_filter_reason"] == (
        "feeder_observation_missing"
    )


def test_missing_context_fail_closed_returns_empty() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(fail_closed=True),
    )

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context={},
    )

    assert result == []
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is False
    assert policy.last_diagnostics["rl_safety_filter_reason"] == (
        "feeder_observation_missing"
    )


def test_unavailable_advisory_is_neutral_fail_open() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
    )
    base = ClosestPolicy().rank(request("closest"), candidates())

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(grid_advisories={}),
    )

    assert [item.station_id for item in result] == [
        item.station_id for item in base
    ]
    assert all(
        item.metadata["rl_safety_status"] == "unavailable"
        for item in result
    )
    assert all(item.metadata["rl_safety_penalty"] == 0.0 for item in result)
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is True
    assert policy.last_diagnostics["rl_safety_filter_reason"] == (
        "grid_advisory_unavailable"
    )
    assert all(item.metadata["fallback_used"] is True for item in result)
    assert all(
        item.metadata["rl_safety_adjusted_score"]
        == item.metadata["base_preference_score"]
        for item in result
    )


def test_partial_advisory_missing_components_are_neutral() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(penalty_weight=0.5),
    )
    context = complete_context()
    context["grid_advisories"] = {
        station_id: {"stress_score": 0.4}
        for station_id in context["feeder_station_ids"]
    }

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=context,
    )

    assert all(
        item.metadata["rl_safety_penalty"] == pytest.approx(0.12)
        for item in result
    )
    assert all(
        item.metadata["rl_safety_adjusted_score"]
        == pytest.approx(item.metadata["base_preference_score"] - 0.06)
        for item in result
    )


def test_block_mode_removes_only_block_eligible_candidate() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(mode="block"),
    )
    context = complete_context()
    context["grid_advisories"] = {
        station_id: {
            "opf_feasible": station_id != "near",
            "verdict": "REJECT" if station_id == "near" else "ACCEPT",
            "risk_class": "VIOLATION" if station_id == "near" else "SAFE",
        }
        for station_id in context["feeder_station_ids"]
    }
    base_remaining = [
        item.station_id
        for item in ClosestPolicy().rank(request("closest"), candidates())
        if item.station_id != "near"
    ]

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=context,
    )

    assert [item.station_id for item in result] == base_remaining
    assert policy.last_diagnostics["rl_safety_filter_blocked_count"] == 1


def test_all_blocked_fail_closed_returns_empty_policy_result() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(mode="block", fail_closed=True),
    )
    context = complete_context()
    context["grid_advisories"] = {
        station_id: {
            "opf_feasible": False,
            "verdict": "REJECT",
            "risk_class": "VIOLATION",
        }
        for station_id in context["feeder_station_ids"]
    }

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=context,
    )

    assert result == []
    assert policy.last_diagnostics["rl_safety_filter_blocked_count"] == len(
        candidates()
    )
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is False


def test_all_blocked_fail_open_restores_policy_order_and_diagnostics() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(mode="block", fail_closed=False),
    )
    context = complete_context()
    context["grid_advisories"] = {
        station_id: {
            "opf_feasible": False,
            "verdict": "REJECT",
            "risk_class": "VIOLATION",
        }
        for station_id in context["feeder_station_ids"]
    }
    base = ClosestPolicy().rank(request("closest"), candidates())

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=context,
    )

    assert [item.station_id for item in result] == [
        item.station_id for item in base
    ]
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is True
    assert policy.last_diagnostics["rl_safety_filter_reason"] == (
        "all_candidates_blocked_fail_open"
    )
    assert all(item.metadata["fallback_used"] is True for item in result)
    assert all(SAFETY_METADATA_KEYS.issubset(item.metadata) for item in result)


def test_exact_only_all_unmapped_is_not_applied() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        FakeFeederPolicy(
            FeederActionPrediction(
                available=True,
                action_index=0,
                station_id="feeder-only",
                fallback_used=False,
                error=None,
            )
        ),
        config=safety_config(mapping_mode="exact_only"),
    )
    base = ClosestPolicy().rank(request("closest"), candidates())
    context = complete_context(
        feeder_station_ids=["feeder-only"],
        feeder_action_mask=[True],
        grid_advisories={"feeder-only": {"stress_score": 1.0}},
    )

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=context,
    )

    assert [item.station_id for item in result] == [
        item.station_id for item in base
    ]
    assert all(item.metadata["rl_safety_status"] == "unmapped" for item in result)
    assert all(item.metadata["rl_safety_penalty"] == 0.0 for item in result)
    assert all(
        item.metadata["rl_safety_mapping_kind"] == "unmapped"
        for item in result
    )
    assert all(
        item.metadata["rl_safety_mapping_physical_claim"] is False
        for item in result
    )
    assert all(
        item.metadata["rl_safety_reason"] == "no_candidate_feeder_mapping"
        for item in result
    )
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False


def test_checkpoint_selected_action_does_not_replace_final_ranker() -> None:
    policy = build_hybrid_policy_for_test(
        "rl_safety_closest",
        FakeFeederPolicy(
            FeederActionPrediction(
                available=True,
                action_index=1,
                station_id="cheap",
                fallback_used=False,
                error=None,
            )
        ),
    )

    result = policy.rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )

    assert result[0].station_id == "near"
    assert result[0].metadata["final_ranker"] == "closest"


def test_safety_metadata_shape_is_stable_across_paths() -> None:
    normal = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
    ).rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )[0]
    unmapped = build_hybrid_policy_for_test(
        "rl_safety_closest",
        FakeFeederPolicy(
            FeederActionPrediction(True, 0, "feeder-only", False, None)
        ),
        config=safety_config(mapping_mode="exact_only"),
    ).rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(
            feeder_station_ids=["feeder-only"],
            feeder_action_mask=[True],
            grid_advisories={},
        ),
    )[0]
    fail_open = build_hybrid_policy_for_test(
        "rl_safety_closest",
        unavailable_inference("checkpoint_missing"),
    ).rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(),
    )[0]
    bridge = build_hybrid_policy_for_test(
        "rl_safety_closest",
        FakeFeederPolicy(
            FeederActionPrediction(True, 0, "feeder-only", False, None)
        ),
        config=safety_config(mapping_mode="stable_ordinal_demo_bridge"),
    ).rank(
        request("closest"),
        candidates(),
        runtime_context=complete_context(
            feeder_station_ids=["feeder-only"],
            feeder_action_mask=[True],
            grid_advisories={"feeder-only": {"stress_score": 0.0}},
        ),
    )[0]
    block_context = complete_context()
    block_context["grid_advisories"] = {
        station_id: {
            "opf_feasible": station_id != "near",
            "verdict": "REJECT" if station_id == "near" else "ACCEPT",
            "risk_class": "VIOLATION" if station_id == "near" else "SAFE",
        }
        for station_id in block_context["feeder_station_ids"]
    }
    block_survivor = build_hybrid_policy_for_test(
        "rl_safety_closest",
        zero_safety_inference(),
        config=safety_config(mode="block"),
    ).rank(
        request("closest"),
        candidates(),
        runtime_context=block_context,
    )[0]

    for item in (normal, unmapped, fail_open, bridge, block_survivor):
        assert SAFETY_METADATA_KEYS.issubset(item.metadata)
    assert bridge.metadata["rl_safety_mapping_kind"] == (
        "stable_ordinal_demo_bridge"
    )
    assert bridge.metadata["rl_safety_mapping_physical_claim"] is False
    assert bridge.metadata["offline_feeder_rl_adapter"] is True
