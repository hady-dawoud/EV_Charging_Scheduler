"""Verify RL safety filtering preserves deterministic preference ranking."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.contracts.responses import RecommendationOption, RecommendationResponse
from ev_core.recommender.baseline_policies import (
    CheapestPolicy,
    ClosestPolicy,
    FastestPolicy,
    WeightedScorePolicy,
)
from ev_core.recommender.feeder_rl_policy import (
    FeederActionPrediction,
    FeederMaskablePPORuntimePolicy,
)
from ev_core.recommender.ranker import CandidateContext, RecommendationInput
from ev_core.recommender.rl_safety_filter import (
    AdvisorySafety,
    CandidateFeederMapping,
    CandidateSafety,
    RLSafetyCheapestPolicy,
    RLSafetyClosestPolicy,
    RLSafetyFastestPolicy,
    RLSafetyFilterConfig,
    RLSafetyPreferencePolicy,
    RLSafetyWeightedPolicy,
    _mapping_metadata,
    apply_safety_to_options,
    build_candidate_safety,
    map_candidates_to_feeder,
)


POLICY_CASES = (
    ("closest", "rl_safety_closest"),
    ("cheapest", "rl_safety_cheapest"),
    ("fastest", "rl_safety_fastest"),
    ("weighted_score", "rl_safety_weighted"),
)
PREFERENCE_CASES = ("closest", "cheapest", "fastest")
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
PRICING_METADATA_KEYS = (
    "price_per_kwh",
    "final_price_per_kwh",
    "dynamic_pricing_enabled",
    "dynamic_pricing_metadata",
)
SAFETY_METADATA_KEYS = (
    "base_preference_score",
    "rl_safety_penalty",
    "rl_safety_penalty_weight",
    "rl_safety_adjusted_score",
    "rl_safety_score",
    "rl_safety_status",
    "rl_safety_reason",
    "rl_safety_mapping_kind",
    "rl_safety_mapping_physical_claim",
)
LIMITATIONS = (
    "offline recorded feeder context",
    "stable ordinal bridge is nonphysical app/demo mapping",
    "primary grid-performance evidence remains feeder evaluator evidence",
)


class VerifierFailure(AssertionError):
    """Raised when the verifier detects a contract failure."""


@dataclass
class FakeFeederPolicy:
    prediction: FeederActionPrediction

    def predict_feeder_action(
        self,
        runtime_context: dict[str, object],
    ) -> FeederActionPrediction:
        return self.prediction


def compare_baseline_and_hybrid(
    *,
    baseline_response: RecommendationResponse,
    hybrid_response: RecommendationResponse,
    expected_final_ranker: str,
) -> dict[str, Any]:
    baseline_options = _response_options(baseline_response)
    hybrid_options = _response_options(hybrid_response)
    if not hybrid_options:
        raise VerifierFailure("hybrid response has no options")
    result = {
        "schema_unchanged": _schema_fields(baseline_response)
        == _schema_fields(hybrid_response),
        "option_schema_unchanged": RecommendationOption.model_fields.keys()
        == RecommendationOption.model_fields.keys(),
        "raw_fields_unchanged": _raw_fields_by_station(baseline_options)
        == _raw_fields_by_station(hybrid_options),
        "final_ranker_preserved": _final_ranker(
            hybrid_response,
            hybrid_options,
        )
        == expected_final_ranker,
        "station_order": [option.station_id for option in hybrid_options],
        "pricing_metadata_present": all(
            _has_pricing_metadata(option) for option in hybrid_options
        ),
        "safety_metadata_present": all(
            _has_safety_metadata(option) for option in hybrid_options
        ),
        "fallback_status_present": _fallback_status_present(
            hybrid_response,
            hybrid_options,
        ),
        "mapping_kind_present": all(
            "rl_safety_mapping_kind" in option.metadata
            for option in hybrid_options
        ),
        "mapping_physical_claim_present": all(
            "rl_safety_mapping_physical_claim" in option.metadata
            for option in hybrid_options
        ),
        "mapping_claims_valid": _mapping_claims_valid(hybrid_options),
    }
    if not result["schema_unchanged"]:
        raise VerifierFailure("response schema changed")
    if not result["safety_metadata_present"]:
        raise VerifierFailure("missing safety metadata")
    if not result["raw_fields_unchanged"]:
        raise VerifierFailure("raw option fields changed")
    if not result["final_ranker_preserved"]:
        raise VerifierFailure("final ranker was not preserved")
    if not result["pricing_metadata_present"]:
        raise VerifierFailure("pricing metadata missing")
    if not result["fallback_status_present"]:
        raise VerifierFailure("fallback status missing")
    if not result["mapping_claims_valid"]:
        raise VerifierFailure(
            "stable ordinal bridge must remain nonphysical",
        )
    return result


def run_synthetic_safety_cases(
    *,
    mapping_mode: str,
    penalty_weight: float,
) -> dict[str, dict[str, Any]]:
    base = [
        _option("risky", score=0.90),
        _option("safe", score=0.70),
        _option("spare", score=0.50),
    ]
    results: dict[str, dict[str, Any]] = {}

    zero_weight = apply_safety_to_options(
        base_options=base[:2],
        safety_by_station={
            "safe": _candidate_safety("safe", penalty=0.0),
            "risky": _candidate_safety("risky", penalty=1.0),
        },
        penalty_weight=0.0,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )
    results["penalty_weight_zero_preserves_order"] = _case_result(
        [item.station_id for item in zero_weight.options] == ["risky", "safe"],
        order=[item.station_id for item in zero_weight.options],
    )

    zero_penalties = apply_safety_to_options(
        base_options=base[:2],
        safety_by_station={
            "safe": _candidate_safety("safe", penalty=0.0),
            "risky": _candidate_safety("risky", penalty=0.0),
        },
        penalty_weight=penalty_weight,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )
    results["all_zero_penalties_preserve_order"] = _case_result(
        [item.station_id for item in zero_penalties.options]
        == ["risky", "safe"],
        order=[item.station_id for item in zero_penalties.options],
    )

    demotion = apply_safety_to_options(
        base_options=base[:2],
        safety_by_station={
            "safe": _candidate_safety("safe", penalty=0.0),
            "risky": _candidate_safety(
                "risky",
                penalty=1.0,
                status="risky",
            ),
        },
        penalty_weight=max(penalty_weight, 0.5),
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )
    results["risky_candidate_demoted"] = _case_result(
        [item.station_id for item in demotion.options] == ["safe", "risky"],
        order=[item.station_id for item in demotion.options],
    )

    mappings = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="exact_only",
    )
    safety = build_candidate_safety(
        candidate_station_ids=["dundee-a"],
        mappings=mappings,
        grid_advisories={"feeder-a": {"stress_score": 1.0}},
        selected_feeder_station_id="feeder-a",
        shared_metadata={},
    )["dundee-a"]
    results["exact_only_unmatched_unpenalized"] = _case_result(
        safety.mapping.mapping_kind == "unmapped"
        and safety.penalty == 0.0
        and safety.mapping.physical_claim is False,
        mapping_kind=safety.mapping.mapping_kind,
        penalty=safety.penalty,
    )

    bridge_a = map_candidates_to_feeder(
        candidate_station_ids=["dundee-b", "dundee-a"],
        feeder_station_ids=["z", "a"],
        feeder_action_mask=[True, True],
        mapping_mode="stable_ordinal_demo_bridge",
    )
    bridge_b = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a", "dundee-b"],
        feeder_station_ids=["z", "a"],
        feeder_action_mask=[True, True],
        mapping_mode="stable_ordinal_demo_bridge",
    )
    bridge_ok = (
        bridge_a == bridge_b
        and all(not mapping.physical_claim for mapping in bridge_a.values())
        and all(
            mapping.mapping_kind == "stable_ordinal_demo_bridge"
            for mapping in bridge_a.values()
        )
    )
    results["stable_ordinal_bridge_deterministic_nonphysical"] = _case_result(
        bridge_ok,
        mapping_mode="stable_ordinal_demo_bridge",
        mapping={
            key: value.feeder_station_id
            for key, value in sorted(bridge_a.items())
        },
    )

    block = apply_safety_to_options(
        base_options=base[:2],
        safety_by_station={
            "safe": _candidate_safety("safe", penalty=0.0),
            "risky": _candidate_safety(
                "risky",
                penalty=1.0,
                blocked=True,
                status="risky",
            ),
        },
        penalty_weight=penalty_weight,
        mode="block",
        block_unsafe=False,
        fail_closed=False,
    )
    results["block_mode_removes_unsafe"] = _case_result(
        [item.station_id for item in block.options] == ["safe"],
        blocked_count=block.blocked_count,
    )

    all_blocked_open = apply_safety_to_options(
        base_options=base[:2],
        safety_by_station={
            "safe": _candidate_safety("safe", penalty=1.0, blocked=True),
            "risky": _candidate_safety("risky", penalty=1.0, blocked=True),
        },
        penalty_weight=penalty_weight,
        mode="block",
        block_unsafe=False,
        fail_closed=False,
    )
    results["all_blocked_fail_open_restores_order"] = _case_result(
        [item.station_id for item in all_blocked_open.options]
        == ["risky", "safe"]
        and all_blocked_open.fallback_used,
        order=[item.station_id for item in all_blocked_open.options],
        fallback_used=all_blocked_open.fallback_used,
    )

    all_blocked_closed = apply_safety_to_options(
        base_options=base[:1],
        safety_by_station={
            "risky": _candidate_safety("risky", penalty=1.0, blocked=True),
        },
        penalty_weight=penalty_weight,
        mode="block",
        block_unsafe=False,
        fail_closed=True,
    )
    results["all_blocked_fail_closed_empty"] = _case_result(
        all_blocked_closed.options == (),
        option_count=len(all_blocked_closed.options),
    )
    return results


def run_verification(args: argparse.Namespace) -> dict[str, Any]:
    if not 0.0 <= args.penalty_weight <= 1.0:
        raise VerifierFailure("--penalty-weight must be in [0.0, 1.0]")
    policy_results = [
        _run_policy_case(
            baseline_name=baseline,
            hybrid_name=hybrid,
            mapping_mode=args.mapping_mode,
            penalty_weight=args.penalty_weight,
        )
        for baseline, hybrid in POLICY_CASES
    ]
    preference_results = [
        _run_preference_case(
            preference_mode=preference,
            mapping_mode=args.mapping_mode,
            penalty_weight=args.penalty_weight,
        )
        for preference in PREFERENCE_CASES
    ]
    synthetic_results = run_synthetic_safety_cases(
        mapping_mode=args.mapping_mode,
        penalty_weight=args.penalty_weight,
    )
    checkpoint = _run_checkpoint_check(strict=args.strict)
    return {
        "passed": True,
        "strict": args.strict,
        "mapping_mode": args.mapping_mode,
        "penalty_weight": args.penalty_weight,
        "policy_cases": policy_results,
        "generic_preference_cases": preference_results,
        "synthetic_safety_cases": synthetic_results,
        "checkpoint": checkpoint,
        "limitations": list(LIMITATIONS),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--mapping-mode",
        choices=("exact_only", "stable_ordinal_demo_bridge"),
        default="exact_only",
    )
    parser.add_argument("--penalty-weight", type=float, default=0.25)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run_verification(args)
    except VerifierFailure as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "strict": args.strict,
                    "mapping_mode": args.mapping_mode,
                    "penalty_weight": args.penalty_weight,
                    "error": str(exc),
                    "limitations": list(LIMITATIONS),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


def _run_policy_case(
    *,
    baseline_name: str,
    hybrid_name: str,
    mapping_mode: str,
    penalty_weight: float,
) -> dict[str, Any]:
    request = _request(baseline_name)
    candidates = _candidates()
    baseline_policy = _baseline_policy(baseline_name)
    baseline_options = baseline_policy.rank(request, candidates)
    hybrid_policy = _hybrid_policy(
        hybrid_name,
        mapping_mode=mapping_mode,
        penalty_weight=penalty_weight,
    )
    hybrid_options = hybrid_policy.rank(
        request,
        candidates,
        runtime_context=_complete_context(),
    )
    comparison = compare_baseline_and_hybrid(
        baseline_response=_response(
            baseline_options,
            policy_name=baseline_name,
            metadata={"final_ranker": baseline_name},
        ),
        hybrid_response=_response(
            hybrid_options,
            policy_name=hybrid_name,
            metadata=hybrid_policy.last_diagnostics,
        ),
        expected_final_ranker=baseline_name,
    )
    comparison.update(
        {
            "baseline_policy": baseline_name,
            "hybrid_policy": hybrid_name,
            "baseline_behavior_unchanged_when_safety_disabled": [
                option.station_id for option in baseline_options
            ]
            == [option.station_id for option in hybrid_options],
            "safety_metadata_appears_only_when_enabled": (
                not any(_has_safety_metadata(option) for option in baseline_options)
                and all(_has_safety_metadata(option) for option in hybrid_options)
            ),
            "fallback_used": hybrid_policy.last_diagnostics.get(
                "rl_safety_filter_fallback_used"
            ),
        }
    )
    return comparison


def _run_preference_case(
    *,
    preference_mode: str,
    mapping_mode: str,
    penalty_weight: float,
) -> dict[str, Any]:
    request = _request(preference_mode)
    candidates = _candidates()
    baseline_options = _baseline_policy(preference_mode).rank(request, candidates)
    policy = RLSafetyPreferencePolicy(
        config=_safety_config(
            mapping_mode=mapping_mode,
            penalty_weight=penalty_weight,
        ),
        feeder_policy=FakeFeederPolicy(_prediction("near")),
    )
    hybrid_options = policy.rank(
        request,
        candidates,
        runtime_context=_complete_context(),
    )
    comparison = compare_baseline_and_hybrid(
        baseline_response=_response(
            baseline_options,
            policy_name=preference_mode,
            metadata={"final_ranker": preference_mode},
        ),
        hybrid_response=_response(
            hybrid_options,
            policy_name="rl_safety_preference",
            metadata=policy.last_diagnostics,
        ),
        expected_final_ranker=preference_mode,
    )
    comparison.update(
        {
            "preference_mode": preference_mode,
            "hybrid_policy": "rl_safety_preference",
            "fallback_used": policy.last_diagnostics.get(
                "rl_safety_filter_fallback_used"
            ),
        }
    )
    return comparison


def _run_checkpoint_check(*, strict: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "attempted": False,
        "fallback_used": None,
        "observation_shape": None,
        "action_count": None,
        "valid_action_count": None,
    }
    if not strict:
        return result
    _require_optional_dependencies()
    _require_checkpoint_artifacts()
    from ev_core.recommender.feeder_runtime_context import (
        build_feeder_runtime_context,
    )

    context_result = build_feeder_runtime_context(
        _checkpoint_request(),
        feeder_rl_data_dir=REPO_ROOT / "data" / "processed" / "evside_feeder_rl",
        grid_advisory_mode="recorded",
        strict=True,
    )
    runtime_context = {
        **context_result.runtime_context,
        **context_result.metadata,
    }
    prediction = FeederMaskablePPORuntimePolicy(
        checkpoint_path=REPO_ROOT
        / "models"
        / "rl_feeder_final"
        / "maskable_ppo_feeder_station_selector.zip",
    ).predict_feeder_action(runtime_context)
    attempted = True
    result.update(
        {
            "attempted": attempted,
            "fallback_used": prediction.fallback_used,
            "observation_shape": context_result.metadata.get(
                "feeder_observation_shape"
            ),
            "action_count": context_result.metadata.get("feeder_action_count"),
            "valid_action_count": context_result.metadata.get(
                "feeder_valid_action_count"
            ),
            "selected_action_index": prediction.action_index,
            "selected_station_id": prediction.station_id,
            "error": prediction.error,
            "rl_safety_filter_fallback_used": False,
        }
    )
    if not prediction.available or prediction.fallback_used:
        raise VerifierFailure(
            "strict checkpoint inference failed: "
            f"{prediction.error or 'fallback_used'}"
        )
    return result


def _require_optional_dependencies() -> None:
    missing = []
    for module_name in ("torch", "stable_baselines3", "sb3_contrib"):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
    if missing:
        raise VerifierFailure(
            "strict verifier requires optional packages: "
            + ", ".join(missing)
        )


def _require_checkpoint_artifacts() -> None:
    data_dir = REPO_ROOT / "data" / "processed" / "evside_feeder_rl"
    required = (
        data_dir / "manifest.json",
        data_dir / "feature_stats.json",
        data_dir / "feeder_ev_action_catalog.parquet",
        data_dir / "feeder_request_priors.parquet",
        data_dir / "feeder_grid_advisory_replay.parquet",
        REPO_ROOT
        / "models"
        / "rl_feeder_final"
        / "maskable_ppo_feeder_station_selector.zip",
    )
    missing = [path for path in required if not path.exists()]
    if missing:
        raise VerifierFailure(
            "strict verifier missing required artifacts: "
            + ", ".join(path.as_posix() for path in missing)
        )


def _schema_fields(response: RecommendationResponse) -> tuple[str, ...]:
    return tuple(type(response).model_fields.keys())


def _response_options(
    response: RecommendationResponse,
) -> list[RecommendationOption]:
    return [
        option
        for option in [response.top_recommendation, *response.alternatives]
        if option is not None
    ]


def _raw_fields_by_station(
    options: Sequence[RecommendationOption],
) -> dict[str, dict[str, Any]]:
    return {
        option.station_id: {
            field: getattr(option, field)
            for field in RAW_OPTION_FIELDS
        }
        for option in options
    }


def _final_ranker(
    response: RecommendationResponse,
    options: Sequence[RecommendationOption],
) -> str | None:
    value = response.metadata.get("final_ranker")
    if value is not None:
        return str(value)
    for option in options:
        value = option.metadata.get("final_ranker")
        if value is not None:
            return str(value)
    return None


def _has_pricing_metadata(option: RecommendationOption) -> bool:
    return all(key in option.metadata for key in PRICING_METADATA_KEYS)


def _has_safety_metadata(option: RecommendationOption) -> bool:
    return all(key in option.metadata for key in SAFETY_METADATA_KEYS)


def _fallback_status_present(
    response: RecommendationResponse,
    options: Sequence[RecommendationOption],
) -> bool:
    response_has = "rl_safety_filter_fallback_used" in response.metadata
    option_has = all("fallback_used" in option.metadata for option in options)
    return response_has or option_has


def _mapping_claims_valid(options: Sequence[RecommendationOption]) -> bool:
    for option in options:
        kind = option.metadata.get("rl_safety_mapping_kind")
        claim = option.metadata.get("rl_safety_mapping_physical_claim")
        if kind == "stable_ordinal_demo_bridge" and claim is not False:
            return False
        if kind == "unmapped" and claim is not False:
            return False
    return True


def _case_result(passed: bool, **details: Any) -> dict[str, Any]:
    return {"passed": bool(passed), **details}


def _baseline_policy(name: str):
    policies = {
        "closest": ClosestPolicy(),
        "cheapest": CheapestPolicy(),
        "fastest": FastestPolicy(),
        "weighted_score": WeightedScorePolicy(),
    }
    return policies[name]


def _hybrid_policy(
    name: str,
    *,
    mapping_mode: str,
    penalty_weight: float,
):
    policies = {
        "rl_safety_closest": RLSafetyClosestPolicy,
        "rl_safety_cheapest": RLSafetyCheapestPolicy,
        "rl_safety_fastest": RLSafetyFastestPolicy,
        "rl_safety_weighted": RLSafetyWeightedPolicy,
    }
    return policies[name](
        config=_safety_config(
            mapping_mode=mapping_mode,
            penalty_weight=penalty_weight,
        ),
        feeder_policy=FakeFeederPolicy(_prediction("near")),
    )


def _safety_config(
    *,
    mapping_mode: str,
    penalty_weight: float,
) -> RLSafetyFilterConfig:
    return RLSafetyFilterConfig(
        enabled=True,
        mode="penalty",
        strict=False,
        penalty_weight=penalty_weight,
        block_unsafe=False,
        mapping_mode=mapping_mode,
        fail_closed=False,
    )


def _request(preference_mode: str) -> RecommendationInput:
    return RecommendationInput(
        request_id="verify-rl-safety-preference",
        preference_mode=preference_mode,
        candidates=tuple(_candidates()),
    )


def _candidates() -> list[CandidateContext]:
    return [
        CandidateContext(
            station_id="near",
            station_name="Nearest",
            zone_id="zone",
            transformer_id="tx-near",
            distance_km=0.1,
            estimated_wait_minutes=45,
            estimated_duration_minutes=45,
            estimated_cost_gbp=12.0,
            transformer_headroom_kw=300.0,
            current_queue=3,
            utilization=0.45,
            charger_compatible=True,
            metadata=_pricing_metadata(0.42),
        ),
        CandidateContext(
            station_id="cheap",
            station_name="Cheapest",
            zone_id="zone",
            transformer_id="tx-cheap",
            distance_km=8.0,
            estimated_wait_minutes=20,
            estimated_duration_minutes=50,
            estimated_cost_gbp=2.0,
            transformer_headroom_kw=300.0,
            current_queue=2,
            utilization=0.35,
            charger_compatible=True,
            metadata=_pricing_metadata(0.25),
        ),
        CandidateContext(
            station_id="fast",
            station_name="Fastest",
            zone_id="zone",
            transformer_id="tx-fast",
            distance_km=5.0,
            estimated_wait_minutes=0,
            estimated_duration_minutes=10,
            estimated_cost_gbp=10.0,
            transformer_headroom_kw=300.0,
            current_queue=0,
            utilization=0.20,
            charger_compatible=True,
            metadata=_pricing_metadata(0.39),
        ),
        CandidateContext(
            station_id="balanced",
            station_name="Balanced",
            zone_id="zone",
            transformer_id="tx-balanced",
            distance_km=2.0,
            estimated_wait_minutes=8,
            estimated_duration_minutes=30,
            estimated_cost_gbp=5.0,
            transformer_headroom_kw=500.0,
            current_queue=1,
            utilization=0.20,
            charger_compatible=True,
            metadata=_pricing_metadata(0.31),
        ),
    ]


def _pricing_metadata(price: float) -> dict[str, Any]:
    return {
        "price_per_kwh": price,
        "final_price_per_kwh": price,
        "dynamic_pricing_enabled": True,
        "dynamic_pricing_metadata": {"price_per_kwh": price},
    }


def _complete_context(**overrides: Any) -> dict[str, Any]:
    station_ids = [candidate.station_id for candidate in _candidates()]
    context: dict[str, Any] = {
        "feeder_observation": [0.0, 0.0, 0.0, 0.0],
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
        "feeder_area_strategy": "synthetic_verifier",
        "feeder_valid_action_count": len(station_ids),
        "grid_truth_level": "recorded",
        "grid_label_source_kind": "recorded_replay",
    }
    context.update(overrides)
    return context


def _prediction(station_id: str) -> FeederActionPrediction:
    station_ids = [candidate.station_id for candidate in _candidates()]
    return FeederActionPrediction(
        available=True,
        action_index=station_ids.index(station_id),
        station_id=station_id,
        fallback_used=False,
        error=None,
    )


def _option(station_id: str, *, score: float) -> RecommendationOption:
    return RecommendationOption(
        station_id=station_id,
        station_name=f"Station {station_id}",
        zone_id="zone",
        transformer_id="tx",
        score=score,
        distance_km=2.0,
        estimated_wait_minutes=10,
        estimated_duration_minutes=30,
        estimated_cost_gbp=5.0,
        transformer_headroom_kw=100.0,
        current_queue=1,
        utilization=0.5,
        charger_compatible=True,
        reason_tags=["synthetic"],
        metadata=_pricing_metadata(0.31),
    )


def _candidate_safety(
    station_id: str,
    *,
    penalty: float,
    blocked: bool = False,
    status: str = "safe",
) -> CandidateSafety:
    mapping = CandidateFeederMapping(
        candidate_station_id=station_id,
        feeder_station_id=station_id,
        action_index=0,
        mapping_kind="exact",
        physical_claim=True,
        reason="exact_or_documented_candidate_feeder_mapping",
    )
    bounded = max(0.0, min(float(penalty), 1.0))
    advisory = AdvisorySafety(
        penalty=bounded,
        score=1.0 - bounded,
        status=status,
        reason="recorded_grid_advisory",
        block_eligible=blocked,
        components={},
    )
    return CandidateSafety(
        station_id=station_id,
        status=status,
        score=advisory.score,
        penalty=bounded,
        reason=advisory.reason,
        blocked=blocked,
        mapping=mapping,
        advisory=advisory,
        metadata=_mapping_metadata(mapping, {}),
    )


def _response(
    options: Sequence[RecommendationOption],
    *,
    policy_name: str,
    metadata: Mapping[str, Any],
) -> RecommendationResponse:
    return RecommendationResponse(
        request_id="verify-rl-safety-preference",
        simulated_timestamp=datetime(2026, 6, 15, tzinfo=timezone.utc),
        top_recommendation=options[0] if options else None,
        alternatives=list(options[1:]),
        debug_reasoning_summary="rl safety preference verifier",
        source_type="verification",
        metadata={"policy_name": policy_name, **dict(metadata)},
    )


def _checkpoint_request() -> SimpleNamespace:
    now = datetime(2024, 6, 10, 12, 0)
    return SimpleNamespace(
        client_request_id="verify-rl-safety-preference",
        request_timestamp=now,
        current_latitude=56.462,
        current_longitude=-2.9707,
        target_soc=80.0,
        current_soc=45.0,
        battery_kwh=60.0,
        requested_energy_kwh=21.0,
        preference_mode="closest",
        charger_type="Any",
        latest_finish_ts=now + timedelta(hours=3),
        source_type="external_live",
        request_id="verify-rl-safety-preference",
        zone_id="zone_central_waterfront",
        metadata={"verification_script": Path(__file__).name},
    )


if __name__ == "__main__":
    raise SystemExit(main())
