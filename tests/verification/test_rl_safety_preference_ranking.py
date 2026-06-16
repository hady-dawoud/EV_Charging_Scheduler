from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ev_core.contracts.responses import RecommendationOption, RecommendationResponse
from scripts.verification.verify_rl_safety_preference_ranking import (
    VerifierFailure,
    compare_baseline_and_hybrid,
    run_synthetic_safety_cases,
)


def option(
    station_id: str,
    *,
    score: float,
    safety_metadata: dict[str, object] | None = None,
    mapping_kind: str = "exact",
    physical_claim: bool = True,
) -> RecommendationOption:
    metadata = {
        "price_per_kwh": 0.31,
        "final_price_per_kwh": 0.34,
        "dynamic_pricing_enabled": True,
        "dynamic_pricing_metadata": {"multiplier": 1.1},
        "final_ranker": "cheapest",
        "fallback_used": False,
    }
    if safety_metadata is not None:
        metadata.update(
            {
                "base_preference_score": score,
                "rl_safety_penalty": 0.0,
                "rl_safety_penalty_weight": 0.25,
                "rl_safety_adjusted_score": score,
                "rl_safety_score": 1.0,
                "rl_safety_status": "safe",
                "rl_safety_reason": "recorded_grid_advisory",
                "rl_safety_mapping_kind": mapping_kind,
                "rl_safety_mapping_physical_claim": physical_claim,
                "rl_safety_mapping_warning": None,
                "offline_feeder_rl_adapter": (
                    mapping_kind == "stable_ordinal_demo_bridge"
                ),
                "rl_safety_filter_fallback_used": False,
            }
        )
        metadata.update(safety_metadata)
    return RecommendationOption(
        station_id=station_id,
        station_name=f"Station {station_id}",
        zone_id="zone-a",
        transformer_id="tx-a",
        score=score,
        distance_km=2.5,
        estimated_wait_minutes=8,
        estimated_duration_minutes=35,
        estimated_cost_gbp=7.25,
        transformer_headroom_kw=120.0,
        current_queue=1,
        utilization=0.35,
        charger_compatible=True,
        reason_tags=["low_cost"],
        metadata=metadata,
    )


def response(
    options: list[RecommendationOption],
    *,
    policy_name: str = "cheapest",
) -> RecommendationResponse:
    return RecommendationResponse(
        request_id="request-1",
        simulated_timestamp=datetime(2026, 6, 15, tzinfo=timezone.utc),
        top_recommendation=options[0] if options else None,
        alternatives=options[1:],
        debug_reasoning_summary="synthetic verifier fixture",
        source_type="verification",
        metadata={
            "policy_name": policy_name,
            "final_ranker": "cheapest",
            "rl_safety_filter_fallback_used": False,
        },
    )


def baseline_response() -> RecommendationResponse:
    return response(
        [
            option("cheap", score=0.75, safety_metadata=None),
            option("safe", score=0.65, safety_metadata=None),
        ],
        policy_name="cheapest",
    )


def hybrid_response() -> RecommendationResponse:
    return response(
        [
            option("cheap", score=0.75, safety_metadata={}),
            option("safe", score=0.65, safety_metadata={}),
        ],
        policy_name="rl_safety_cheapest",
    )


def test_compare_baseline_and_hybrid_preserves_schema_and_raw_fields() -> None:
    result = compare_baseline_and_hybrid(
        baseline_response=baseline_response(),
        hybrid_response=hybrid_response(),
        expected_final_ranker="cheapest",
    )

    assert result["schema_unchanged"] is True
    assert result["raw_fields_unchanged"] is True
    assert result["final_ranker_preserved"] is True
    assert result["pricing_metadata_present"] is True
    assert result["safety_metadata_present"] is True
    assert result["fallback_status_present"] is True


def test_strict_failure_when_hybrid_lacks_required_safety_metadata() -> None:
    bad = response([option("cheap", score=0.75, safety_metadata=None)])

    with pytest.raises(VerifierFailure, match="missing safety metadata"):
        compare_baseline_and_hybrid(
            baseline_response=baseline_response(),
            hybrid_response=bad,
            expected_final_ranker="cheapest",
        )


def test_strict_failure_when_raw_option_fields_change() -> None:
    changed = hybrid_response()
    assert changed.top_recommendation is not None
    changed.top_recommendation.estimated_cost_gbp = 99.0

    with pytest.raises(VerifierFailure, match="raw option fields changed"):
        compare_baseline_and_hybrid(
            baseline_response=baseline_response(),
            hybrid_response=changed,
            expected_final_ranker="cheapest",
        )


def test_strict_failure_when_stable_ordinal_bridge_claims_physical_identity() -> None:
    bad = response(
        [
            option(
                "cheap",
                score=0.75,
                safety_metadata={},
                mapping_kind="stable_ordinal_demo_bridge",
                physical_claim=True,
            )
        ],
    )

    with pytest.raises(VerifierFailure, match="nonphysical"):
        compare_baseline_and_hybrid(
            baseline_response=response([option("cheap", score=0.75)]),
            hybrid_response=bad,
            expected_final_ranker="cheapest",
        )


def test_exact_mapping_may_claim_physical_identity() -> None:
    result = compare_baseline_and_hybrid(
        baseline_response=response([option("cheap", score=0.75)]),
        hybrid_response=response(
            [
                option(
                    "cheap",
                    score=0.75,
                    safety_metadata={},
                    mapping_kind="exact",
                    physical_claim=True,
                )
            ]
        ),
        expected_final_ranker="cheapest",
    )

    assert result["mapping_claims_valid"] is True


def test_synthetic_safety_cases_cover_required_behaviors() -> None:
    result = run_synthetic_safety_cases(
        mapping_mode="exact_only",
        penalty_weight=0.5,
    )

    assert result["penalty_weight_zero_preserves_order"]["passed"] is True
    assert result["all_zero_penalties_preserve_order"]["passed"] is True
    assert result["risky_candidate_demoted"]["passed"] is True
    assert result["exact_only_unmatched_unpenalized"]["passed"] is True
    assert (
        result["stable_ordinal_bridge_deterministic_nonphysical"]["passed"]
        is True
    )
    assert (
        result["stable_ordinal_bridge_deterministic_nonphysical"]["mapping_mode"]
        == "stable_ordinal_demo_bridge"
    )
    assert result["block_mode_removes_unsafe"]["passed"] is True
    assert result["all_blocked_fail_open_restores_order"]["passed"] is True
    assert result["all_blocked_fail_closed_empty"]["passed"] is True
