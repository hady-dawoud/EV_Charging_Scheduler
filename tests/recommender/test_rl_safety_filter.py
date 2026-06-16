from __future__ import annotations

import ast
import inspect
import importlib.util
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ev_core.contracts.responses import RecommendationOption
from ev_core.recommender.rl_safety_filter import (
    CURTAILMENT_RISK_SCALE_KW,
    AdvisorySafety,
    CandidateFeederMapping,
    CandidateSafety,
    _mapping_metadata,
    apply_safety_to_options,
    advisory_safety,
    build_candidate_safety,
    classify_safety_status,
    map_candidates_to_feeder,
)


def test_curtailment_scale_is_named_and_matches_current_action_power() -> None:
    assert CURTAILMENT_RISK_SCALE_KW == 22.0


def test_advisory_risk_uses_documented_weights() -> None:
    result = advisory_safety(
        {
            "stress_score": 0.5,
            "voltage_violation_count": 1,
            "line_overload_count": 0,
            "trafo_overload_count": 1,
            "opf_feasible": False,
            "curtailment_required_kw": 11.0,
            "verdict": "REJECT",
            "risk_class": "VIOLATION",
        }
    )

    assert result.penalty == pytest.approx(
        0.30 * 0.5
        + 0.15 * 1.0
        + 0.15 * 0.0
        + 0.15 * 1.0
        + 0.15 * 1.0
        + 0.10 * 0.5
    )
    assert result.score == pytest.approx(1.0 - result.penalty)
    assert result.status == "risky"
    assert result.block_eligible is True


@pytest.mark.parametrize(
    ("penalty", "status"),
    [
        (0.0, "safe"),
        (0.2499, "safe"),
        (0.25, "caution"),
        (0.5999, "caution"),
        (0.60, "risky"),
        (1.0, "risky"),
    ],
)
def test_safety_status_boundaries(penalty: float, status: str) -> None:
    assert classify_safety_status(penalty) == status


def test_partial_advisory_fields_are_neutral_in_fail_open_scoring() -> None:
    result = advisory_safety({"stress_score": 0.4})

    assert result.penalty == pytest.approx(0.30 * 0.4)
    assert result.score == pytest.approx(0.88)
    assert result.block_eligible is False


def test_missing_advisory_is_unavailable() -> None:
    result = advisory_safety(None)

    assert result.status == "unavailable"
    assert result.penalty == 0.0
    assert result.score == 1.0
    assert result.reason == "grid_advisory_unavailable"
    assert result.block_eligible is False
    assert result.components == {}


@pytest.mark.parametrize(
    "advisory",
    [
        {"verdict": "REJECT"},
        {"risk_class": "VIOLATION"},
        {"opf_feasible": False},
    ],
)
def test_explicit_grid_failures_are_block_eligible(advisory: dict[str, object]) -> None:
    result = advisory_safety(advisory)

    assert result.block_eligible is True


class AttributeAdvisory:
    stress_score = 0.5
    voltage_violation_count = 1
    line_overload_count = 0
    trafo_overload_count = 0
    opf_feasible = True
    curtailment_required_kw = 0.0
    verdict = "OK"
    risk_class = "SAFE"


def test_attribute_based_advisory_objects_are_supported() -> None:
    result = advisory_safety(AttributeAdvisory())

    assert result.penalty == pytest.approx(0.30)
    assert result.score == pytest.approx(0.70)
    assert result.status == "caution"
    assert result.block_eligible is False


def test_malformed_fields_are_neutral_and_fail_open() -> None:
    result = advisory_safety(
        {
            "stress_score": "not-a-number",
            "voltage_violation_count": object(),
            "line_overload_count": float("nan"),
            "trafo_overload_count": float("inf"),
            "opf_feasible": "not-a-boolean",
            "curtailment_required_kw": float("-inf"),
            "verdict": object(),
            "risk_class": object(),
        }
    )

    assert result.penalty == 0.0
    assert result.score == 1.0
    assert result.status == "safe"
    assert result.block_eligible is False


@pytest.mark.parametrize(
    "advisory",
    [
        {
            "stress_score": 1000.0,
            "voltage_violation_count": 10,
            "line_overload_count": 10,
            "trafo_overload_count": 10,
            "opf_feasible": False,
            "curtailment_required_kw": 1000.0,
        },
        {
            "stress_score": -1000.0,
            "voltage_violation_count": -10,
            "line_overload_count": -10,
            "trafo_overload_count": -10,
            "curtailment_required_kw": -1000.0,
        },
    ],
)
def test_scores_and_penalties_are_bounded(advisory: dict[str, object]) -> None:
    result = advisory_safety(advisory)

    assert 0.0 <= result.penalty <= 1.0
    assert 0.0 <= result.score <= 1.0


def test_advisory_safety_result_is_immutable() -> None:
    result = advisory_safety(None)

    with pytest.raises(FrozenInstanceError):
        result.score = 0.0

    assert isinstance(result, AdvisorySafety)


def test_safety_filter_has_no_torch_or_sb3_imports() -> None:
    spec = importlib.util.find_spec("ev_core.recommender.rl_safety_filter")
    assert spec is not None
    assert spec.origin is not None
    tree = ast.parse(Path(spec.origin).read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imported_roots.isdisjoint({"torch", "stable_baselines3", "sb3_contrib"})


def test_exact_station_id_mapping_has_physical_claim() -> None:
    result = map_candidates_to_feeder(
        candidate_station_ids=["feeder-b", "dundee-a"],
        feeder_station_ids=["feeder-a", "feeder-b"],
        feeder_action_mask=[True, True],
        mapping_mode="exact_only",
        documented_mapping={},
    )

    mapping = result["feeder-b"]
    assert mapping.mapping_kind == "exact"
    assert mapping.physical_claim is True
    assert mapping.feeder_station_id == "feeder-b"
    assert mapping.action_index == 1


def test_exact_station_id_takes_precedence_over_documented_mapping() -> None:
    result = map_candidates_to_feeder(
        candidate_station_ids=["feeder-a"],
        feeder_station_ids=["feeder-a", "feeder-b"],
        feeder_action_mask=[True, True],
        mapping_mode="exact_only",
        documented_mapping={"feeder-a": "feeder-b"},
    )

    assert result["feeder-a"].feeder_station_id == "feeder-a"
    assert result["feeder-a"].action_index == 0


def test_documented_mapping_table_is_used_after_exact_id_match() -> None:
    result = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="exact_only",
        documented_mapping={"dundee-a": "feeder-a"},
    )

    mapping = result["dundee-a"]
    assert mapping.mapping_kind == "exact"
    assert mapping.physical_claim is True
    assert mapping.feeder_station_id == "feeder-a"


def test_exact_only_unmatched_candidate_is_unmapped_and_unpenalized() -> None:
    result = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="exact_only",
        documented_mapping={},
    )

    mapping = result["dundee-a"]
    assert mapping.mapping_kind == "unmapped"
    assert mapping.physical_claim is False
    assert mapping.feeder_station_id is None
    assert mapping.action_index is None
    assert mapping.reason == "no_candidate_feeder_mapping"


def test_documented_mapping_to_masked_action_remains_unmapped() -> None:
    result = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[False],
        mapping_mode="exact_only",
        documented_mapping={"dundee-a": "feeder-a"},
    )

    assert result["dundee-a"].mapping_kind == "unmapped"
    assert result["dundee-a"].feeder_station_id is None


def test_stable_ordinal_bridge_is_deterministic_and_sorted() -> None:
    first = map_candidates_to_feeder(
        candidate_station_ids=["dundee-c", "dundee-a", "dundee-b"],
        feeder_station_ids=["feeder-z", "feeder-a"],
        feeder_action_mask=[True, True],
        mapping_mode="stable_ordinal_demo_bridge",
        documented_mapping={},
    )
    second = map_candidates_to_feeder(
        candidate_station_ids=["dundee-b", "dundee-c", "dundee-a"],
        feeder_station_ids=["feeder-z", "feeder-a"],
        feeder_action_mask=[True, True],
        mapping_mode="stable_ordinal_demo_bridge",
        documented_mapping={},
    )

    assert first == second
    assert first["dundee-a"].feeder_station_id == "feeder-a"
    assert first["dundee-b"].feeder_station_id == "feeder-z"
    assert first["dundee-c"].feeder_station_id == "feeder-a"
    assert first["dundee-a"].mapping_kind == "stable_ordinal_demo_bridge"
    assert first["dundee-a"].physical_claim is False
    assert first["dundee-a"].warning == "nonphysical_demo_mapping"


def test_mapping_metadata_labels_exact_mapping_as_physical() -> None:
    mapping = map_candidates_to_feeder(
        candidate_station_ids=["feeder-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="exact_only",
    )["feeder-a"]

    metadata = _mapping_metadata(mapping, {})

    assert metadata["rl_safety_mapping_kind"] == "exact"
    assert metadata["rl_safety_mapping_physical_claim"] is True
    assert metadata["offline_feeder_rl_adapter"] is False
    assert metadata["rl_safety_mapping_warning"] is None


def test_mapping_metadata_labels_unmapped_candidate_without_physical_claim() -> None:
    mapping = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="exact_only",
    )["dundee-a"]

    metadata = _mapping_metadata(mapping, {})

    assert metadata["rl_safety_mapping_kind"] == "unmapped"
    assert metadata["rl_safety_mapping_physical_claim"] is False
    assert metadata["rl_safety_reason"] == "no_candidate_feeder_mapping"
    assert metadata["offline_feeder_rl_adapter"] is False
    assert metadata["rl_safety_mapping_warning"] is None


def test_mapping_metadata_labels_ordinal_bridge_as_nonphysical_demo() -> None:
    mapping = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="stable_ordinal_demo_bridge",
    )["dundee-a"]

    metadata = _mapping_metadata(
        mapping,
        {
            "rl_selected_feeder_station_id": "feeder-a",
            "rl_selected_action_index": 0,
            "grid_truth_level": "recorded",
        },
    )

    assert metadata["rl_safety_mapping_kind"] == "stable_ordinal_demo_bridge"
    assert metadata["rl_safety_mapping_physical_claim"] is False
    assert metadata["offline_feeder_rl_adapter"] is True
    assert metadata["rl_safety_mapping_warning"] == "nonphysical_demo_mapping"
    assert metadata["rl_selected_feeder_station_id"] == "feeder-a"
    assert metadata["rl_selected_action_index"] == 0
    assert metadata["grid_truth_level"] == "recorded"


def test_mapping_module_does_not_use_python_hash_for_persistent_mapping() -> None:
    source = inspect.getsource(map_candidates_to_feeder)

    assert "hash(" not in source


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


def option(station_id: str, score: float) -> RecommendationOption:
    return RecommendationOption(
        station_id=station_id,
        station_name=f"Station {station_id}",
        zone_id="zone",
        transformer_id="tx",
        score=score,
        distance_km=2.5,
        estimated_wait_minutes=12,
        estimated_duration_minutes=45,
        estimated_cost_gbp=7.25,
        transformer_headroom_kw=85.0,
        current_queue=2,
        utilization=0.65,
        charger_compatible=True,
        reason_tags=["base"],
        metadata={
            "price_per_kwh": 0.31,
            "final_price_per_kwh": 0.31,
            "dynamic_pricing_enabled": True,
            "dynamic_pricing_metadata": {"tariff": "peak"},
        },
    )


def candidate_safety(
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
    advisory = AdvisorySafety(
        penalty=penalty,
        score=1.0 - max(0.0, min(penalty, 1.0)),
        status=status,
        reason="recorded_grid_advisory",
        block_eligible=blocked,
        components={},
    )
    return CandidateSafety(
        station_id=station_id,
        status=status,
        score=advisory.score,
        penalty=penalty,
        reason=advisory.reason,
        blocked=blocked,
        mapping=mapping,
        advisory=advisory,
        metadata=_mapping_metadata(mapping, {}),
    )


def test_penalty_formula_and_higher_score_direction() -> None:
    result = apply_safety_to_options(
        base_options=[
            option("safe", score=0.7),
            option("risky", score=0.9),
        ],
        safety_by_station={
            "safe": candidate_safety("safe", penalty=0.0),
            "risky": candidate_safety(
                "risky",
                penalty=1.0,
                status="risky",
            ),
        },
        penalty_weight=0.5,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["safe", "risky"]
    assert result.options[0].score == pytest.approx(0.7)
    assert result.options[1].score == pytest.approx(0.4)


def test_penalty_and_weight_are_bounded() -> None:
    result = apply_safety_to_options(
        base_options=[option("risky", score=0.9)],
        safety_by_station={
            "risky": candidate_safety("risky", penalty=4.0, status="risky"),
        },
        penalty_weight=3.0,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    adjusted = result.options[0]
    assert adjusted.score == pytest.approx(-0.1)
    assert adjusted.metadata["rl_safety_penalty"] == 1.0
    assert adjusted.metadata["rl_safety_penalty_weight"] == 1.0


def test_zero_penalty_weight_preserves_original_order() -> None:
    base = [option("first", score=0.6), option("second", score=0.5)]
    result = apply_safety_to_options(
        base_options=base,
        safety_by_station={
            "first": candidate_safety("first", penalty=1.0),
            "second": candidate_safety("second", penalty=0.0),
        },
        penalty_weight=0.0,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["first", "second"]


def test_zero_candidate_penalties_preserve_original_order() -> None:
    base = [option("first", score=0.6), option("second", score=0.5)]
    result = apply_safety_to_options(
        base_options=base,
        safety_by_station={
            "first": candidate_safety("first", penalty=0.0),
            "second": candidate_safety("second", penalty=0.0),
        },
        penalty_weight=1.0,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["first", "second"]


def test_equal_adjusted_scores_keep_wrapped_policy_order() -> None:
    base = [option("first", score=0.8), option("second", score=0.7)]
    result = apply_safety_to_options(
        base_options=base,
        safety_by_station={
            "first": candidate_safety("first", penalty=0.2),
            "second": candidate_safety("second", penalty=0.1),
        },
        penalty_weight=1.0,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["first", "second"]


def test_raw_option_fields_and_dynamic_pricing_metadata_are_unchanged() -> None:
    base_option = option("station", score=0.8)
    raw_before = {
        field: getattr(base_option, field)
        for field in RAW_OPTION_FIELDS
    }
    pricing_before = {
        key: base_option.metadata[key]
        for key in (
            "price_per_kwh",
            "final_price_per_kwh",
            "dynamic_pricing_enabled",
            "dynamic_pricing_metadata",
        )
    }

    result = apply_safety_to_options(
        base_options=[base_option],
        safety_by_station={
            "station": candidate_safety("station", penalty=0.2),
        },
        penalty_weight=0.5,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    adjusted = result.options[0]
    assert {
        field: getattr(adjusted, field)
        for field in RAW_OPTION_FIELDS
    } == raw_before
    assert {
        key: adjusted.metadata[key]
        for key in pricing_before
    } == pricing_before
    assert adjusted.reason_tags == base_option.reason_tags


def test_adjusted_option_exposes_stable_safety_metadata() -> None:
    result = apply_safety_to_options(
        base_options=[option("station", score=0.8)],
        safety_by_station={
            "station": candidate_safety("station", penalty=0.2),
        },
        penalty_weight=0.5,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    metadata = result.options[0].metadata
    assert metadata["base_preference_score"] == 0.8
    assert metadata["rl_safety_penalty"] == 0.2
    assert metadata["rl_safety_penalty_weight"] == 0.5
    assert metadata["rl_safety_adjusted_score"] == pytest.approx(0.7)
    assert {
        "rl_safety_filter_enabled",
        "rl_safety_filter_mode",
        "rl_safety_status",
        "rl_safety_score",
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
    }.issubset(metadata)


def test_all_blocked_fail_open_restores_original_order() -> None:
    base = [option("first", score=0.8), option("second", score=0.7)]
    result = apply_safety_to_options(
        base_options=base,
        safety_by_station={
            "first": candidate_safety("first", penalty=1.0, blocked=True),
            "second": candidate_safety("second", penalty=1.0, blocked=True),
        },
        penalty_weight=0.25,
        mode="block",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["first", "second"]
    assert result.fallback_used is True
    assert result.applied is False
    assert result.reason == "all_candidates_blocked_fail_open"
    assert all(item.metadata["fallback_used"] is True for item in result.options)


def test_all_blocked_fail_closed_returns_empty() -> None:
    result = apply_safety_to_options(
        base_options=[option("only", score=0.8)],
        safety_by_station={
            "only": candidate_safety("only", penalty=1.0, blocked=True),
        },
        penalty_weight=0.25,
        mode="block",
        block_unsafe=False,
        fail_closed=True,
    )

    assert result.options == ()
    assert result.fallback_used is False
    assert result.blocked_count == 1


def test_block_mode_removes_only_block_eligible_candidates() -> None:
    result = apply_safety_to_options(
        base_options=[
            option("unsafe", score=0.9),
            option("safe", score=0.6),
        ],
        safety_by_station={
            "unsafe": candidate_safety(
                "unsafe",
                penalty=0.8,
                blocked=True,
                status="risky",
            ),
            "safe": candidate_safety("safe", penalty=0.0),
        },
        penalty_weight=0.25,
        mode="block",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["safe"]
    assert result.blocked_count == 1
    assert result.fallback_used is False


def test_block_unsafe_removes_candidate_in_penalty_mode() -> None:
    result = apply_safety_to_options(
        base_options=[
            option("unsafe", score=0.9),
            option("safe", score=0.6),
        ],
        safety_by_station={
            "unsafe": candidate_safety(
                "unsafe",
                penalty=0.8,
                blocked=True,
                status="risky",
            ),
            "safe": candidate_safety("safe", penalty=0.0),
        },
        penalty_weight=0.25,
        mode="penalty",
        block_unsafe=True,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["safe"]
    assert result.blocked_count == 1


def test_selected_feeder_action_changes_reason_only() -> None:
    mapping = CandidateFeederMapping(
        candidate_station_id="candidate-a",
        feeder_station_id="feeder-a",
        action_index=0,
        mapping_kind="exact",
        physical_claim=True,
        reason="exact_or_documented_candidate_feeder_mapping",
    )
    advisory = {
        "stress_score": 0.4,
        "opf_feasible": True,
        "verdict": "ACCEPT",
        "risk_class": "CAUTION",
    }

    selected = build_candidate_safety(
        candidate_station_ids=["candidate-a"],
        mappings={"candidate-a": mapping},
        grid_advisories={"feeder-a": advisory},
        selected_feeder_station_id="feeder-a",
        shared_metadata={},
    )["candidate-a"]
    unselected = build_candidate_safety(
        candidate_station_ids=["candidate-a"],
        mappings={"candidate-a": mapping},
        grid_advisories={"feeder-a": advisory},
        selected_feeder_station_id="feeder-b",
        shared_metadata={},
    )["candidate-a"]

    assert selected.reason == "checkpoint_selected_recorded_advisory"
    assert unselected.reason == "recorded_grid_advisory"
    assert selected.penalty == unselected.penalty == pytest.approx(0.12)
    assert selected.status == unselected.status == "safe"


def test_selected_feeder_action_does_not_override_blocked_advisory() -> None:
    mapping = CandidateFeederMapping(
        candidate_station_id="candidate-a",
        feeder_station_id="feeder-a",
        action_index=0,
        mapping_kind="exact",
        physical_claim=True,
        reason="exact_or_documented_candidate_feeder_mapping",
    )

    safety = build_candidate_safety(
        candidate_station_ids=["candidate-a"],
        mappings={"candidate-a": mapping},
        grid_advisories={
            "feeder-a": {
                "stress_score": 0.9,
                "opf_feasible": False,
                "verdict": "REJECT",
                "risk_class": "VIOLATION",
            }
        },
        selected_feeder_station_id="feeder-a",
        shared_metadata={},
    )["candidate-a"]

    assert safety.reason == "checkpoint_selected_recorded_advisory"
    assert safety.blocked is True
    assert safety.penalty > 0.0


def test_mapped_advisory_values_produce_expected_safety() -> None:
    mapping = CandidateFeederMapping(
        candidate_station_id="candidate-a",
        feeder_station_id="feeder-a",
        action_index=0,
        mapping_kind="exact",
        physical_claim=True,
        reason="exact_or_documented_candidate_feeder_mapping",
    )

    safety = build_candidate_safety(
        candidate_station_ids=["candidate-a"],
        mappings={"candidate-a": mapping},
        grid_advisories={
            "feeder-a": {
                "stress_score": 0.5,
                "voltage_violation_count": 1,
                "opf_feasible": True,
            }
        },
        selected_feeder_station_id=None,
        shared_metadata={},
    )["candidate-a"]

    assert safety.penalty == pytest.approx(0.30)
    assert safety.score == pytest.approx(0.70)
    assert safety.status == "caution"
    assert safety.blocked is False


def test_missing_mapped_advisory_is_unavailable_and_neutral() -> None:
    mapping = CandidateFeederMapping(
        candidate_station_id="candidate-a",
        feeder_station_id="feeder-a",
        action_index=0,
        mapping_kind="exact",
        physical_claim=True,
        reason="exact_or_documented_candidate_feeder_mapping",
    )

    safety = build_candidate_safety(
        candidate_station_ids=["candidate-a"],
        mappings={"candidate-a": mapping},
        grid_advisories={},
        selected_feeder_station_id=None,
        shared_metadata={},
    )["candidate-a"]

    assert safety.status == "unavailable"
    assert safety.penalty == 0.0
    assert safety.score == 1.0
    assert safety.blocked is False
    assert safety.reason == "grid_advisory_unavailable"
