# RL Safety Filter With Preference Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five hybrid recommendation policies that use the existing feeder checkpoint and recorded advisories as a bounded safety layer while preserving the existing closest, cheapest, fastest, and weighted deterministic rankers as the final ordering logic.

**Architecture:** Introduce a dependency-light `rl_safety_filter.py` module containing pure safety scoring, candidate-to-feeder mapping, and hybrid policy wrappers. Refactor the existing feeder policy to expose one reusable lazy checkpoint-prediction result, then compose that result with options already ranked by existing deterministic policies. Policy selection enables hybrid behavior explicitly or through configuration; `DundeeEnv` builds feeder context only for raw feeder RL or hybrid safety paths, and `RecommendationService` merges diagnostics into existing metadata without changing response contracts.

**Tech Stack:** Python 3.10+, dataclasses, Pydantic, NumPy, existing EV Core recommendation policies, optional PyTorch/Stable-Baselines3/sb3-contrib, pytest.

---

## Non-Goals

This plan must not introduce:

- changes to `ExternalChargingRequest`;
- changes to `RecommendationOption`;
- changes to `RecommendationResponse`;
- API/mobile schema changes;
- checkpoint retraining or checkpoint replacement;
- changes to the 2200-feature feeder observation;
- feeder reward changes;
- forecast features in RL observations or safety scoring;
- live DigitalTwin closed-loop control;
- MARL;
- fabricated physical Dundee-to-feeder station identity;
- app success-rate claims as feeder grid-performance evidence;
- PR 6.1 exporter implementation;
- PR 6.3 hybrid thesis benchmarking.

The ordinal bridge remains nonphysical app/demo evidence only. Primary
grid-performance evidence remains the paused feeder-evaluator infrastructure.

## Files

### Create

- `packages/ev_core/src/ev_core/recommender/rl_safety_filter.py`
  - Pure risk scoring, mapping, hybrid result contracts, and policy wrappers.
- `tests/recommender/test_rl_safety_filter.py`
  - Pure scoring, mapping, penalty, blocking, and immutability tests.
- `tests/recommender/test_rl_safety_policies.py`
  - Wrapped policy selection, checkpoint integration, and failure-mode tests.
- `scripts/verification/verify_rl_safety_preference_ranking.py`
  - Baseline/hybrid runtime verifier.

### Modify

- `packages/ev_core/src/ev_core/config/recommendation.py`
  - Safety config, validation, hybrid policy names, and automatic policy mapping.
- `packages/ev_core/src/ev_core/recommender/feeder_rl_policy.py`
  - Reusable feeder action-prediction result without changing raw feeder policy behavior.
- `packages/ev_core/src/ev_core/recommender/policy_registry.py`
  - Register five hybrid policies.
- `packages/ev_core/src/ev_core/recommender/service.py`
  - Merge stable hybrid diagnostics into response metadata.
- `packages/ev_core/src/ev_core/env/dundee_env.py`
  - Build feeder context for hybrid policies and automatic safety activation.
- `services/sim_runtime/runtime_manager.py`
  - Carry safety configuration into status and selection metadata.
- `apps/api/app/services/runtime_service.py`
  - Populate runtime safety configuration from `RecommendationConfig`.
- `tests/config/test_routing_pricing_recommendation_config.py`
  - Config defaults, parsing, validation, and policy selection.
- `tests/recommender/test_policy_registry.py`
  - Hybrid registration and dependency-lazy import behavior.
- `tests/recommender/test_feeder_rl_policy_diagnostics.py`
  - Shared prediction-result regression coverage.
- `tests/recommender/test_recommendation_service.py`
  - Response diagnostics and schema preservation.
- `tests/recommender/test_dundee_env_recommendation_policy.py`
  - Hybrid feeder-context trigger and preference preservation.
- `tests/api/test_app_recommendation_mapping.py`
  - Automatic and explicit hybrid policy selection.
- `tests/api/test_runtime_service_recommendation_policy_config.py`
  - Runtime safety config propagation.
- `tests/sim_runtime/test_runtime_recommendation_policy.py`
  - Runtime status and metadata propagation.
- `docs/ai_context/RECOMMENDER_FLOW.md`
- `docs/ai_context/REQUEST_FLOW.md`
- `docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md`
- `docs/ai_context/RL_READINESS_REPORT.md`
- `docs/ai_context/RUNTIME_ARTIFACTS_AND_MODEL_LOADING.md`
- `docs/ai_context/OPEN_QUESTIONS.md`
- `docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md`
- `docs/ev_side/OFFLINE_FEEDER_RL_FORECASTING_PR_PLAN.md`
- `.env.feeder_rl_demo.example`

### Do Not Modify

- `packages/ev_core/src/ev_core/contracts/requests.py`
- `packages/ev_core/src/ev_core/contracts/responses.py`
- `packages/ev_core/src/ev_core/rl_feeder/observations.py`
- `packages/ev_core/src/ev_core/rl_feeder/rewards.py`
- files under `models/`
- PR 6.1 design or plan documents.

## Phase A: Config, Pure Scoring, And Mapping

### Task 1: Add Safety Configuration And Hybrid Policy Resolution

**Files:**
- Modify: `packages/ev_core/src/ev_core/config/recommendation.py`
- Modify: `tests/config/test_routing_pricing_recommendation_config.py`
- Modify: `tests/api/test_app_recommendation_mapping.py`

- [ ] **Step 1: Write failing config-default and policy-name tests**

Add:

```python
def test_recommendation_safety_defaults_are_conservative() -> None:
    config = RecommendationConfig()

    assert config.rl_safety_filter_enabled is False
    assert config.rl_safety_filter_mode == "penalty"
    assert config.rl_safety_filter_strict is False
    assert config.rl_safety_filter_penalty_weight == 0.25
    assert config.rl_safety_block_unsafe is False
    assert config.rl_safety_mapping_mode == "exact_only"


def test_known_policies_include_all_hybrid_names() -> None:
    assert {
        "rl_safety_closest",
        "rl_safety_cheapest",
        "rl_safety_fastest",
        "rl_safety_weighted",
        "rl_safety_preference",
    }.issubset(KNOWN_RECOMMENDATION_POLICIES)
```

Add environment parsing coverage:

```python
def test_recommendation_config_reads_rl_safety_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RL_SAFETY_FILTER_ENABLED", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_MODE", "block")
    monkeypatch.setenv("RL_SAFETY_FILTER_STRICT", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_PENALTY_WEIGHT", "0.75")
    monkeypatch.setenv("RL_SAFETY_BLOCK_UNSAFE", "true")
    monkeypatch.setenv("RL_SAFETY_MAPPING_MODE", "stable_ordinal_demo_bridge")

    config = recommendation_config_from_env()

    assert config.rl_safety_filter_enabled is True
    assert config.rl_safety_filter_mode == "block"
    assert config.rl_safety_filter_strict is True
    assert config.rl_safety_filter_penalty_weight == 0.75
    assert config.rl_safety_block_unsafe is True
    assert config.rl_safety_mapping_mode == "stable_ordinal_demo_bridge"
```

- [ ] **Step 2: Write failing validation tests**

Add:

```python
@pytest.mark.parametrize("value", ["unknown", "soft"])
def test_invalid_rl_safety_mode_fails(value: str) -> None:
    with pytest.raises(ValueError, match="rl_safety_filter_mode"):
        RecommendationConfig(rl_safety_filter_mode=value)


@pytest.mark.parametrize("value", ["hash_bridge", "nearest"])
def test_invalid_rl_safety_mapping_mode_fails(value: str) -> None:
    with pytest.raises(ValueError, match="rl_safety_mapping_mode"):
        RecommendationConfig(rl_safety_mapping_mode=value)


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_invalid_rl_safety_penalty_weight_fails(value: float) -> None:
    with pytest.raises(ValueError, match="rl_safety_filter_penalty_weight"):
        RecommendationConfig(rl_safety_filter_penalty_weight=value)
```

- [ ] **Step 3: Write failing automatic and explicit selection tests**

Add:

```python
def test_enabled_safety_maps_preference_policy_to_hybrid() -> None:
    selection = select_recommendation_policy(
        preference_mode="cheapest",
        config=RecommendationConfig(
            policy_name="",
            rl_safety_filter_enabled=True,
        ),
    )

    assert selection.requested_policy_name == "cheapest"
    assert selection.effective_policy_name == "rl_safety_cheapest"
    assert selection.preference_mode == "cheapest"


def test_explicit_hybrid_policy_self_enables_when_global_flag_is_false() -> None:
    selection = select_recommendation_policy(
        preference_mode="closest",
        explicit_policy_name="rl_safety_preference",
        config=RecommendationConfig(policy_name="", rl_safety_filter_enabled=False),
    )

    assert selection.effective_policy_name == "rl_safety_preference"
    assert selection.rl_safety_filter_enabled is True


def test_disabled_safety_keeps_normal_preference_policy() -> None:
    selection = select_recommendation_policy(
        preference_mode="fastest",
        config=RecommendationConfig(policy_name="", rl_safety_filter_enabled=False),
    )

    assert selection.effective_policy_name == "fastest"
```

- [ ] **Step 4: Run tests and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic pytest tests\config\test_routing_pricing_recommendation_config.py tests\api\test_app_recommendation_mapping.py -q
```

Expected: failures for missing fields, constants, validation, and hybrid policy mapping.

- [ ] **Step 5: Implement config constants and validation**

Add:

```python
RL_SAFETY_FILTER_MODES = frozenset({"penalty", "block"})
RL_SAFETY_MAPPING_MODES = frozenset({"exact_only", "stable_ordinal_demo_bridge"})
RL_SAFETY_HYBRID_POLICIES = frozenset(
    {
        "rl_safety_closest",
        "rl_safety_cheapest",
        "rl_safety_fastest",
        "rl_safety_weighted",
        "rl_safety_preference",
    }
)
RL_SAFETY_POLICY_BY_BASE = {
    "closest": "rl_safety_closest",
    "cheapest": "rl_safety_cheapest",
    "fastest": "rl_safety_fastest",
    "weighted_score": "rl_safety_weighted",
}
```

Extend the frozen dataclass:

```python
@dataclass(frozen=True)
class RecommendationConfig:
    policy_name: str = "weighted_score"
    force_policy_name: str | None = None
    fallback_policy_name: str = "weighted_score"
    max_alternatives: int = 3
    rl_policy_fail_closed: bool = False
    rl_feeder_checkpoint_path: Path | None = None
    feeder_data_dir: Path | None = None
    rl_safety_filter_enabled: bool = False
    rl_safety_filter_mode: str = "penalty"
    rl_safety_filter_strict: bool = False
    rl_safety_filter_penalty_weight: float = 0.25
    rl_safety_block_unsafe: bool = False
    rl_safety_mapping_mode: str = "exact_only"

    def __post_init__(self) -> None:
        if self.rl_safety_filter_mode not in RL_SAFETY_FILTER_MODES:
            raise ValueError(
                "rl_safety_filter_mode must be one of: "
                + ", ".join(sorted(RL_SAFETY_FILTER_MODES))
            )
        if self.rl_safety_mapping_mode not in RL_SAFETY_MAPPING_MODES:
            raise ValueError(
                "rl_safety_mapping_mode must be one of: "
                + ", ".join(sorted(RL_SAFETY_MAPPING_MODES))
            )
        if not 0.0 <= float(self.rl_safety_filter_penalty_weight) <= 1.0:
            raise ValueError("rl_safety_filter_penalty_weight must be between 0.0 and 1.0.")
```

- [ ] **Step 6: Implement selection mapping and metadata**

Add fields to `PolicySelection`:

```python
rl_safety_filter_enabled: bool
rl_safety_filter_mode: str
rl_safety_filter_strict: bool
rl_safety_filter_penalty_weight: float
rl_safety_block_unsafe: bool
rl_safety_mapping_mode: str
```

Add:

```python
def is_rl_safety_policy(policy_name: str | None) -> bool:
    return str(policy_name or "") in RL_SAFETY_HYBRID_POLICIES


def _effective_safety_policy(
    policy_name: str,
    *,
    safety_enabled: bool,
) -> str:
    if is_rl_safety_policy(policy_name):
        return policy_name
    if safety_enabled:
        return RL_SAFETY_POLICY_BY_BASE.get(policy_name, policy_name)
    return policy_name
```

Refactor `select_recommendation_policy` to first resolve the existing precedence
into `requested` and `source`, then compute:

```python
explicit_hybrid = is_rl_safety_policy(requested)
safety_enabled = bool(cfg.rl_safety_filter_enabled or explicit_hybrid)
effective = _effective_safety_policy(requested, safety_enabled=safety_enabled)
```

Preserve original `preference_mode` and `requested_policy_name`. Add all safety
fields to `PolicySelection.metadata()`.

- [ ] **Step 7: Parse environment variables**

In `recommendation_config_from_env()` add:

```python
rl_safety_filter_enabled=_bool_from_env(
    os.getenv("RL_SAFETY_FILTER_ENABLED"),
    False,
),
rl_safety_filter_mode=os.getenv("RL_SAFETY_FILTER_MODE", "penalty").strip().lower(),
rl_safety_filter_strict=_bool_from_env(
    os.getenv("RL_SAFETY_FILTER_STRICT"),
    False,
),
rl_safety_filter_penalty_weight=float(
    os.getenv("RL_SAFETY_FILTER_PENALTY_WEIGHT", "0.25")
),
rl_safety_block_unsafe=_bool_from_env(
    os.getenv("RL_SAFETY_BLOCK_UNSAFE"),
    False,
),
rl_safety_mapping_mode=os.getenv(
    "RL_SAFETY_MAPPING_MODE",
    "exact_only",
).strip().lower(),
```

- [ ] **Step 8: Run tests and verify GREEN**

Run the Step 4 command.

Expected: all config and API selection tests pass.

- [ ] **Step 9: Commit Phase A config**

```powershell
git add packages/ev_core/src/ev_core/config/recommendation.py tests/config/test_routing_pricing_recommendation_config.py tests/api/test_app_recommendation_mapping.py
git commit -m "feat: add RL safety recommendation config"
```

### Task 2: Add Pure Advisory Risk Scoring

**Files:**
- Create: `packages/ev_core/src/ev_core/recommender/rl_safety_filter.py`
- Create: `tests/recommender/test_rl_safety_filter.py`

- [ ] **Step 1: Write failing risk-component tests**

Create:

```python
from __future__ import annotations

import pytest

from ev_core.recommender.rl_safety_filter import (
    CURTAILMENT_RISK_SCALE_KW,
    advisory_safety,
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
```

- [ ] **Step 2: Write failing boundary and partial-field tests**

Add:

```python
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
    from ev_core.recommender.rl_safety_filter import classify_safety_status

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
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_rl_safety_filter.py -q
```

Expected: import failure because `rl_safety_filter.py` does not exist.

- [ ] **Step 4: Implement immutable scoring result and constants**

Create:

```python
from dataclasses import dataclass
from typing import Any, Mapping

CURTAILMENT_RISK_SCALE_KW = 22.0
SAFE_PENALTY_LIMIT = 0.25
RISKY_PENALTY_LIMIT = 0.60


@dataclass(frozen=True)
class AdvisorySafety:
    penalty: float
    score: float
    status: str
    reason: str
    block_eligible: bool
    components: dict[str, float]


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(max(float(value), low), high)


def classify_safety_status(penalty: float) -> str:
    bounded = clamp(penalty)
    if bounded < SAFE_PENALTY_LIMIT:
        return "safe"
    if bounded < RISKY_PENALTY_LIMIT:
        return "caution"
    return "risky"
```

Implement field access for dicts or Pydantic advisory objects:

```python
def _value(advisory: object, name: str, default: Any) -> Any:
    if isinstance(advisory, Mapping):
        return advisory.get(name, default)
    return getattr(advisory, name, default)
```

Implement exactly:

```python
def advisory_safety(advisory: object | None) -> AdvisorySafety:
    if advisory is None:
        return AdvisorySafety(
            penalty=0.0,
            score=1.0,
            status="unavailable",
            reason="grid_advisory_unavailable",
            block_eligible=False,
            components={},
        )
    components = {
        "stress_risk": clamp(_as_float(_value(advisory, "stress_score", 0.0))),
        "voltage_risk": float(_as_int(_value(advisory, "voltage_violation_count", 0)) > 0),
        "line_risk": float(_as_int(_value(advisory, "line_overload_count", 0)) > 0),
        "transformer_risk": float(_as_int(_value(advisory, "trafo_overload_count", 0)) > 0),
        "opf_risk": float(not bool(_value(advisory, "opf_feasible", True))),
        "curtailment_risk": clamp(
            _as_float(_value(advisory, "curtailment_required_kw", 0.0))
            / CURTAILMENT_RISK_SCALE_KW
        ),
    }
    risk = clamp(
        0.30 * components["stress_risk"]
        + 0.15 * components["voltage_risk"]
        + 0.15 * components["line_risk"]
        + 0.15 * components["transformer_risk"]
        + 0.15 * components["opf_risk"]
        + 0.10 * components["curtailment_risk"]
    )
    verdict = str(_value(advisory, "verdict", "")).upper()
    risk_class = str(_value(advisory, "risk_class", "")).upper()
    block_eligible = (
        verdict == "REJECT"
        or risk_class == "VIOLATION"
        or components["opf_risk"] == 1.0
    )
    return AdvisorySafety(
        penalty=risk,
        score=1.0 - risk,
        status=classify_safety_status(risk),
        reason="recorded_grid_advisory",
        block_eligible=block_eligible,
        components=components,
    )
```

- [ ] **Step 5: Run tests and verify GREEN**

Run the Step 3 command.

Expected: all scoring tests pass without importing Torch/SB3.

- [ ] **Step 6: Commit pure scoring**

```powershell
git add packages/ev_core/src/ev_core/recommender/rl_safety_filter.py tests/recommender/test_rl_safety_filter.py
git commit -m "feat: add bounded RL safety scoring"
```

### Task 3: Add Exact And Stable Ordinal Mapping

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/rl_safety_filter.py`
- Modify: `tests/recommender/test_rl_safety_filter.py`

- [ ] **Step 1: Write failing exact-mapping tests**

Add:

```python
def test_exact_station_id_mapping_has_physical_claim() -> None:
    from ev_core.recommender.rl_safety_filter import map_candidates_to_feeder

    result = map_candidates_to_feeder(
        candidate_station_ids=["feeder-b", "dundee-a"],
        feeder_station_ids=["feeder-a", "feeder-b"],
        feeder_action_mask=[True, True],
        mapping_mode="exact_only",
        documented_mapping={},
    )

    assert result["feeder-b"].mapping_kind == "exact"
    assert result["feeder-b"].physical_claim is True
    assert result["feeder-b"].feeder_station_id == "feeder-b"
    assert result["feeder-b"].action_index == 1
```

Add documented mapping coverage:

```python
def test_documented_mapping_table_is_used_after_exact_id_match() -> None:
    result = map_candidates_to_feeder(
        candidate_station_ids=["dundee-a"],
        feeder_station_ids=["feeder-a"],
        feeder_action_mask=[True],
        mapping_mode="exact_only",
        documented_mapping={"dundee-a": "feeder-a"},
    )

    assert result["dundee-a"].mapping_kind == "exact"
    assert result["dundee-a"].physical_claim is True
```

- [ ] **Step 2: Write failing exact-only and bridge tests**

Add:

```python
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
    assert mapping.reason == "no_candidate_feeder_mapping"


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
```

- [ ] **Step 3: Add source guard against persistent Python hash**

Add:

```python
def test_mapping_module_does_not_use_python_hash_for_persistent_mapping() -> None:
    import inspect
    import ev_core.recommender.rl_safety_filter as module

    source = inspect.getsource(module.map_candidates_to_feeder)

    assert "hash(" not in source
```

- [ ] **Step 4: Run tests and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_rl_safety_filter.py -q
```

Expected: failures for missing mapping contracts.

- [ ] **Step 5: Implement mapping result and precedence**

Add:

```python
@dataclass(frozen=True)
class CandidateFeederMapping:
    candidate_station_id: str
    feeder_station_id: str | None
    action_index: int | None
    mapping_kind: str
    physical_claim: bool
    reason: str
    warning: str | None = None
```

Implement:

```python
def map_candidates_to_feeder(
    *,
    candidate_station_ids: Sequence[str],
    feeder_station_ids: Sequence[str],
    feeder_action_mask: Sequence[bool],
    mapping_mode: str,
    documented_mapping: Mapping[str, str] | None = None,
) -> dict[str, CandidateFeederMapping]:
    station_ids = [str(value) for value in feeder_station_ids]
    valid_pairs = sorted(
        (
            (station_id, index)
            for index, (station_id, allowed) in enumerate(
                zip(station_ids, feeder_action_mask)
            )
            if bool(allowed)
        ),
        key=lambda item: (item[0], item[1]),
    )
    valid_by_id = {station_id: index for station_id, index in valid_pairs}
    documented = {
        str(candidate_id): str(feeder_id)
        for candidate_id, feeder_id in (documented_mapping or {}).items()
    }
    result: dict[str, CandidateFeederMapping] = {}
    unmatched: list[str] = []
    for candidate_id in sorted(str(value) for value in candidate_station_ids):
        mapped_id = candidate_id if candidate_id in valid_by_id else documented.get(candidate_id)
        if mapped_id in valid_by_id:
            result[candidate_id] = CandidateFeederMapping(
                candidate_station_id=candidate_id,
                feeder_station_id=mapped_id,
                action_index=valid_by_id[mapped_id],
                mapping_kind="exact",
                physical_claim=True,
                reason="exact_or_documented_candidate_feeder_mapping",
            )
        else:
            unmatched.append(candidate_id)
    if mapping_mode == "stable_ordinal_demo_bridge" and valid_pairs:
        for ordinal, candidate_id in enumerate(unmatched):
            feeder_id, action_index = valid_pairs[ordinal % len(valid_pairs)]
            result[candidate_id] = CandidateFeederMapping(
                candidate_station_id=candidate_id,
                feeder_station_id=feeder_id,
                action_index=action_index,
                mapping_kind="stable_ordinal_demo_bridge",
                physical_claim=False,
                reason="stable_ordinal_nonphysical_demo_mapping",
                warning="nonphysical_demo_mapping",
            )
    else:
        for candidate_id in unmatched:
            result[candidate_id] = CandidateFeederMapping(
                candidate_station_id=candidate_id,
                feeder_station_id=None,
                action_index=None,
                mapping_kind="unmapped",
                physical_claim=False,
                reason="no_candidate_feeder_mapping",
            )
    return result
```

The documented table key in runtime context is:

```text
candidate_feeder_station_map
```

Only verified/documented mappings may populate it.

- [ ] **Step 6: Implement the exact mapping metadata contract**

Add one `_mapping_metadata` helper and test its literal output keys. It must
return:

```python
def _mapping_metadata(
    mapping: CandidateFeederMapping,
    shared_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    metadata = {
        "rl_safety_mapping_kind": mapping.mapping_kind,
        "rl_safety_mapping_physical_claim": mapping.physical_claim,
        "rl_safety_mapping_warning": mapping.warning,
        "rl_mapped_feeder_station_id": mapping.feeder_station_id,
        "rl_mapped_feeder_action_index": mapping.action_index,
        "rl_selected_feeder_station_id": shared_metadata.get(
            "rl_selected_feeder_station_id"
        ),
        "rl_selected_action_index": shared_metadata.get(
            "rl_selected_action_index"
        ),
        "feeder_selected_secondary_area_id": shared_metadata.get(
            "feeder_selected_secondary_area_id"
        ),
        "feeder_area_strategy": shared_metadata.get("feeder_area_strategy"),
        "feeder_valid_action_count": shared_metadata.get(
            "feeder_valid_action_count"
        ),
        "grid_truth_level": shared_metadata.get("grid_truth_level"),
        "grid_label_source_kind": shared_metadata.get(
            "grid_label_source_kind"
        ),
        "offline_feeder_rl_adapter": (
            mapping.mapping_kind == "stable_ordinal_demo_bridge"
        ),
    }
    return metadata
```

Assert specifically that the ordinal bridge emits:

```python
assert metadata["rl_safety_mapping_kind"] == "stable_ordinal_demo_bridge"
assert metadata["rl_safety_mapping_physical_claim"] is False
assert metadata["offline_feeder_rl_adapter"] is True
assert metadata["rl_safety_mapping_warning"] == "nonphysical_demo_mapping"
```

For exact and unmapped candidates, `offline_feeder_rl_adapter` is false. Keep
the warning key present with `None` when it does not apply so consumers can
inspect one stable shape.

- [ ] **Step 7: Run tests and verify GREEN**

Expected: all scoring and mapping tests pass.

- [ ] **Step 8: Commit mapping**

```powershell
git add packages/ev_core/src/ev_core/recommender/rl_safety_filter.py tests/recommender/test_rl_safety_filter.py
git commit -m "feat: add feeder candidate safety mapping"
```

## Phase B: Base Scores And Hybrid Wrappers

### Task 4: Refactor Feeder Prediction Into A Reusable Result

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/feeder_rl_policy.py`
- Modify: `tests/recommender/test_feeder_rl_policy_diagnostics.py`

- [ ] **Step 1: Write failing reusable prediction tests**

Add:

```python
def test_predict_feeder_action_returns_validated_action_metadata(monkeypatch, tmp_path) -> None:
    checkpoint = tmp_path / "checkpoint.zip"
    checkpoint.write_text("placeholder", encoding="utf-8")
    model = FakeModel(action_index=1, expected_shape=4)
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=checkpoint)
    monkeypatch.setattr(policy, "_load_model", lambda: model)

    prediction = policy.predict_feeder_action(
        {
            "feeder_observation": np.zeros(4, dtype=np.float32),
            "feeder_action_mask": [False, True],
            "feeder_station_ids": ["feeder-a", "feeder-b"],
        }
    )

    assert prediction.available is True
    assert prediction.action_index == 1
    assert prediction.station_id == "feeder-b"
    assert prediction.fallback_used is False
    assert prediction.error is None


def test_predict_feeder_action_returns_controlled_error_without_fallback(monkeypatch) -> None:
    policy = FeederMaskablePPORuntimePolicy(checkpoint_path=Path("missing.zip"))

    prediction = policy.predict_feeder_action({})

    assert prediction.available is False
    assert prediction.action_index is None
    assert prediction.station_id is None
    assert prediction.fallback_used is True
    assert prediction.error == "checkpoint_missing"
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_feeder_rl_policy_diagnostics.py -q
```

Expected: `predict_feeder_action` does not exist.

- [ ] **Step 3: Add prediction result contract**

Add:

```python
@dataclass(frozen=True)
class FeederActionPrediction:
    available: bool
    action_index: int | None
    station_id: str | None
    fallback_used: bool
    error: str | None
```

Add:

```python
def predict_feeder_action(
    self,
    runtime_context: dict[str, Any],
) -> FeederActionPrediction:
    model = self._load_model()
    if model is None:
        return FeederActionPrediction(
            available=False,
            action_index=None,
            station_id=None,
            fallback_used=True,
            error=self._load_error or "feeder_policy_unavailable",
        )
    validated = self._validated_runtime_inputs(model, runtime_context)
    if validated is None:
        return FeederActionPrediction(
            available=False,
            action_index=None,
            station_id=None,
            fallback_used=True,
            error=self._load_error or "feeder_runtime_context_invalid",
        )
    observation, action_mask, station_ids = validated
    try:
        action, _state = model.predict(
            observation,
            deterministic=True,
            action_masks=action_mask,
        )
    except Exception as exc:
        self._load_error = f"prediction_failed: {exc}"
        return FeederActionPrediction(False, None, None, True, self._load_error)
    action_index = int(np.asarray(action).reshape(-1)[0])
    if action_index < 0 or action_index >= len(station_ids):
        self._load_error = "predicted_action_out_of_range"
        return FeederActionPrediction(False, None, None, True, self._load_error)
    if not action_mask[action_index]:
        self._load_error = "predicted_action_masked_out"
        return FeederActionPrediction(False, None, None, True, self._load_error)
    return FeederActionPrediction(
        available=True,
        action_index=action_index,
        station_id=station_ids[action_index],
        fallback_used=False,
        error=None,
    )
```

- [ ] **Step 4: Refactor raw feeder ranking to use the result**

Replace duplicate prediction logic in `_rank_with_feeder_checkpoint` with:

```python
prediction = self.predict_feeder_action(runtime_context)
if not prediction.available:
    return None
action_index = int(prediction.action_index)
selected_station_id = str(prediction.station_id)
```

Keep existing raw feeder mapping, metadata, fail-open, and fail-closed behavior
unchanged.

- [ ] **Step 5: Run regression tests and verify GREEN**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_feeder_rl_policy_diagnostics.py tests\recommender\test_policy_registry.py -q
```

Expected: existing PR 4 policy tests and new prediction tests pass.

- [ ] **Step 6: Commit prediction refactor**

```powershell
git add packages/ev_core/src/ev_core/recommender/feeder_rl_policy.py tests/recommender/test_feeder_rl_policy_diagnostics.py
git commit -m "refactor: expose feeder action prediction"
```

### Task 5: Implement Penalty Application And Immutability

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/rl_safety_filter.py`
- Modify: `tests/recommender/test_rl_safety_filter.py`

- [ ] **Step 1: Write failing penalty equation tests**

Add a helper that builds `RecommendationOption` objects with pricing metadata,
then add:

```python
def test_penalty_formula_and_higher_score_direction() -> None:
    result = apply_safety_to_options(
        base_options=[
            option("safe", score=0.7),
            option("risky", score=0.9),
        ],
        safety_by_station={
            "safe": candidate_safety(penalty=0.0),
            "risky": candidate_safety(penalty=1.0),
        },
        penalty_weight=0.5,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["safe", "risky"]
    assert result.options[0].score == pytest.approx(0.7)
    assert result.options[1].score == pytest.approx(0.4)
```

- [ ] **Step 2: Write zero-weight, zero-penalty, and stable-sort tests**

Add:

```python
def test_zero_penalty_weight_preserves_original_order() -> None:
    base = [option("first", score=0.6), option("second", score=0.5)]
    result = apply_safety_to_options(
        base_options=base,
        safety_by_station={
            "first": candidate_safety(penalty=1.0),
            "second": candidate_safety(penalty=0.0),
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
            "first": candidate_safety(penalty=0.0),
            "second": candidate_safety(penalty=0.0),
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
            "first": candidate_safety(penalty=0.2),
            "second": candidate_safety(penalty=0.1),
        },
        penalty_weight=1.0,
        mode="penalty",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["first", "second"]
```

- [ ] **Step 3: Write raw-field immutability and metadata tests**

Snapshot:

```python
RAW_FIELDS = (
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
```

Assert before/after values match and pricing metadata is unchanged. Assert:

```python
metadata = result.options[0].metadata
assert metadata["base_preference_score"] == 0.8
assert metadata["rl_safety_penalty"] == 0.2
assert metadata["rl_safety_penalty_weight"] == 0.5
assert metadata["rl_safety_adjusted_score"] == 0.7
```

- [ ] **Step 4: Run and verify RED**

Run the focused safety-filter tests.

Expected: missing option-adjustment contracts.

- [ ] **Step 5: Implement candidate and filter result contracts**

Add:

```python
@dataclass(frozen=True)
class CandidateSafety:
    station_id: str
    status: str
    score: float
    penalty: float
    reason: str
    blocked: bool
    mapping: CandidateFeederMapping
    advisory: AdvisorySafety
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SafetyFilterResult:
    options: tuple[RecommendationOption, ...]
    enabled: bool
    applied: bool
    mode: str
    mapping_mode: str
    penalized_count: int
    blocked_count: int
    fallback_used: bool
    reason: str
```

- [ ] **Step 6: Implement score-only adjustment**

Implement:

```python
def apply_safety_to_options(
    *,
    base_options: Sequence[RecommendationOption],
    safety_by_station: Mapping[str, CandidateSafety],
    penalty_weight: float,
    mode: str,
    block_unsafe: bool,
    fail_closed: bool,
    mapping_mode: str = "exact_only",
) -> SafetyFilterResult:
    bounded_weight = clamp(penalty_weight)
    adjusted: list[RecommendationOption] = []
    blocked_count = 0
    penalized_count = 0
    for option in base_options:
        safety = safety_by_station[option.station_id]
        should_block = bool(
            safety.blocked and (mode == "block" or block_unsafe)
        )
        if should_block:
            blocked_count += 1
            continue
        base_score = float(option.score)
        adjusted_score = base_score - bounded_weight * clamp(safety.penalty)
        if safety.penalty > 0.0 and bounded_weight > 0.0:
            penalized_count += 1
        metadata = {
            **option.metadata,
            **safety.metadata,
            "base_preference_score": base_score,
            "rl_safety_filter_enabled": True,
            "rl_safety_filter_mode": mode,
            "rl_safety_penalty": clamp(safety.penalty),
            "rl_safety_penalty_weight": bounded_weight,
            "rl_safety_adjusted_score": adjusted_score,
            "rl_safety_score": clamp(safety.score),
            "rl_safety_status": safety.status,
            "rl_safety_reason": safety.reason,
            "rl_safety_blocked": False,
            "fallback_used": False,
        }
        adjusted.append(
            option.model_copy(
                update={
                    "score": adjusted_score,
                    "metadata": metadata,
                }
            )
        )
    if not adjusted and blocked_count and not fail_closed:
        restored = tuple(
            option.model_copy(
                update={
                    "metadata": {
                        **option.metadata,
                        **safety_by_station[option.station_id].metadata,
                        "base_preference_score": float(option.score),
                        "rl_safety_filter_enabled": True,
                        "rl_safety_filter_mode": mode,
                        "rl_safety_penalty": clamp(
                            safety_by_station[option.station_id].penalty
                        ),
                        "rl_safety_penalty_weight": bounded_weight,
                        "rl_safety_adjusted_score": float(option.score),
                        "rl_safety_score": clamp(
                            safety_by_station[option.station_id].score
                        ),
                        "rl_safety_status": "unavailable",
                        "rl_safety_blocked": False,
                        "rl_safety_reason": (
                            "all_candidates_blocked_fail_open"
                        ),
                        "fallback_used": True,
                        "rl_safety_filter_fallback_used": True,
                        "rl_safety_filter_reason": "all_candidates_blocked_fail_open",
                    }
                }
            )
            for option in base_options
        )
        return SafetyFilterResult(
            options=restored,
            enabled=True,
            applied=False,
            mode=mode,
            mapping_mode=mapping_mode,
            penalized_count=0,
            blocked_count=blocked_count,
            fallback_used=True,
            reason="all_candidates_blocked_fail_open",
        )
    ranked = tuple(sorted(adjusted, key=lambda item: item.score, reverse=True))
    return SafetyFilterResult(
        options=ranked,
        enabled=True,
        applied=bool(penalized_count or blocked_count),
        mode=mode,
        mapping_mode=mapping_mode,
        penalized_count=penalized_count,
        blocked_count=blocked_count,
        fallback_used=False,
        reason="rl_safety_filter_applied",
    )
```

Python sorting is stable, so equal adjusted scores retain wrapped-policy order.
Do not rebuild any raw option fields.

Every returned hybrid option, including fail-open restorations, must expose
this stable metadata shape:

```text
base_preference_score
rl_safety_filter_enabled
rl_safety_filter_mode
rl_safety_status
rl_safety_score
rl_safety_penalty
rl_safety_penalty_weight
rl_safety_adjusted_score
rl_safety_blocked
rl_safety_reason
rl_safety_mapping_kind
rl_safety_mapping_physical_claim
rl_safety_mapping_warning
rl_mapped_feeder_station_id
rl_mapped_feeder_action_index
rl_selected_feeder_station_id
rl_selected_action_index
feeder_selected_secondary_area_id
feeder_area_strategy
feeder_valid_action_count
grid_truth_level
grid_label_source_kind
offline_feeder_rl_adapter
fallback_used
```

Use `None` for conditional values that are unavailable. Do not omit keys in a
way that makes the result shape depend on mapping or inference success.

- [ ] **Step 7: Run tests and verify GREEN**

Expected: penalty, stable-order, and immutability tests pass.

- [ ] **Step 8: Commit penalty application**

```powershell
git add packages/ev_core/src/ev_core/recommender/rl_safety_filter.py tests/recommender/test_rl_safety_filter.py
git commit -m "feat: apply bounded safety penalties"
```

### Task 6: Implement Hybrid Policy Wrappers

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/rl_safety_filter.py`
- Create: `tests/recommender/test_rl_safety_policies.py`

- [ ] **Step 1: Write failing wrapped-ranker selection tests**

Create candidates with competing distance, cost, and duration values. Add:

```python
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
    policy = build_hybrid_policy_for_test(hybrid_name, zero_safety_inference())
    result = policy.rank(
        request(preference_mode),
        candidates(),
        runtime_context=complete_context(),
    )

    assert policy.last_diagnostics["final_ranker"] == expected_final_ranker
    assert result[0].metadata["final_ranker"] == expected_final_ranker
```

- [ ] **Step 2: Write failing base-ranking preservation tests**

For each explicit wrapper, compare its output with the corresponding base policy
when all safety penalties are zero:

```python
@pytest.mark.parametrize(
    ("hybrid", "base"),
    [
        ("rl_safety_closest", ClosestPolicy()),
        ("rl_safety_cheapest", CheapestPolicy()),
        ("rl_safety_fastest", FastestPolicy()),
        ("rl_safety_weighted", WeightedScorePolicy()),
    ],
)
def test_zero_safety_preserves_wrapped_policy_order(hybrid, base) -> None:
    request_value = request("closest")
    candidate_values = candidates()
    base_ids = [
        item.station_id
        for item in base.rank(request_value, candidate_values)
    ]
    hybrid_policy = build_hybrid_policy_for_test(hybrid, zero_safety_inference())
    hybrid_ids = [
        item.station_id
        for item in hybrid_policy.rank(
            request_value,
            candidate_values,
            runtime_context=complete_context(),
        )
    ]

    assert hybrid_ids == base_ids
```

- [ ] **Step 3: Write cheapest dynamic-cost test**

Use candidates whose metadata includes different `final_price_per_kwh` and
whose `estimated_cost_gbp` reflects that dynamic price. Assert the base score:

```python
assert cheap_option.metadata["base_preference_score"] == pytest.approx(
    1.0 / (1.0 + cheap_option.estimated_cost_gbp)
)
assert cheap_option.metadata["final_price_per_kwh"] == 0.31
```

- [ ] **Step 4: Run tests and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_rl_safety_policies.py -q
```

Expected: missing hybrid policy classes.

- [ ] **Step 5: Implement policy configuration adapter**

Add:

```python
@dataclass(frozen=True)
class RLSafetyFilterConfig:
    enabled: bool = False
    mode: str = "penalty"
    strict: bool = False
    penalty_weight: float = 0.25
    block_unsafe: bool = False
    mapping_mode: str = "exact_only"
    fail_closed: bool = False


def safety_config_from_recommendation(
    config: RecommendationConfig,
    *,
    explicit_hybrid: bool,
) -> RLSafetyFilterConfig:
    return RLSafetyFilterConfig(
        enabled=bool(config.rl_safety_filter_enabled or explicit_hybrid),
        mode=config.rl_safety_filter_mode,
        strict=config.rl_safety_filter_strict,
        penalty_weight=config.rl_safety_filter_penalty_weight,
        block_unsafe=config.rl_safety_block_unsafe,
        mapping_mode=config.rl_safety_mapping_mode,
        fail_closed=bool(
            config.rl_safety_filter_strict
            or config.rl_policy_fail_closed
        ),
    )
```

- [ ] **Step 6: Implement hybrid wrapper and explicit classes**

Add:

```python
class RLSafetyPreferencePolicy:
    name = "rl_safety_preference"

    def __init__(
        self,
        *,
        base_policy: RecommendationPolicy | None = None,
        config: RLSafetyFilterConfig | None = None,
        feeder_policy: FeederMaskablePPORuntimePolicy | None = None,
    ) -> None:
        self.base_policy = base_policy
        self.config = config or safety_config_from_recommendation(
            recommendation_config_from_env(),
            explicit_hybrid=True,
        )
        self.feeder_policy = feeder_policy or FeederMaskablePPORuntimePolicy()
        self.last_diagnostics: dict[str, Any] = {}

    def _base_policy(self, preference_mode: str) -> RecommendationPolicy:
        if self.base_policy is not None:
            return self.base_policy
        policies = {
            "closest": ClosestPolicy(),
            "cheapest": CheapestPolicy(),
            "fastest": FastestPolicy(),
            "weighted_score": WeightedScorePolicy(),
        }
        return policies.get(preference_mode, WeightedScorePolicy())
```

Create subclasses:

```python
class RLSafetyClosestPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_closest"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=ClosestPolicy(), **kwargs)


class RLSafetyCheapestPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_cheapest"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=CheapestPolicy(), **kwargs)


class RLSafetyFastestPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_fastest"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=FastestPolicy(), **kwargs)


class RLSafetyWeightedPolicy(RLSafetyPreferencePolicy):
    name = "rl_safety_weighted"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_policy=WeightedScorePolicy(), **kwargs)
```

- [ ] **Step 7: Implement policy rank orchestration**

Within `rank`:

1. Rank with the base policy.
2. Save every original option score as base score.
3. Call `feeder_policy.predict_feeder_action(runtime_context)`.
4. On unavailable prediction, apply fail-open/closed behavior from Phase C.
5. Map candidates.
6. Build candidate safety from mapped advisories.
7. Apply score/block behavior.
8. Attach shared diagnostics to every option.

Use:

```python
base_policy = self._base_policy(request.preference_mode)
base_options = base_policy.rank(
    request,
    candidates,
    runtime_context=runtime_context,
)
final_ranker = base_policy.name
```

Do not copy or restate any deterministic scoring formula.

- [ ] **Step 8: Run tests and verify GREEN**

Expected: wrapped ranker, generic selection, zero-safety, and dynamic-cost tests pass.

- [ ] **Step 9: Commit hybrid wrappers**

```powershell
git add packages/ev_core/src/ev_core/recommender/rl_safety_filter.py tests/recommender/test_rl_safety_policies.py
git commit -m "feat: wrap preference policies with RL safety"
```

## Phase C: Runtime Context, Failure Modes, And Blocking

### Task 7: Complete Candidate Safety Assembly And Failure Modes

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/rl_safety_filter.py`
- Modify: `tests/recommender/test_rl_safety_policies.py`
- Modify: `tests/recommender/test_rl_safety_filter.py`

- [ ] **Step 1: Write failing fail-open and fail-closed tests**

Add:

```python
def test_missing_prediction_fail_open_restores_deterministic_ranking() -> None:
    policy = build_hybrid_policy(
        config=safety_config(fail_closed=False),
        prediction=unavailable_prediction("checkpoint_missing"),
    )

    result = policy.rank(request("closest"), candidates(), runtime_context={})

    assert [item.station_id for item in result] == closest_ids(candidates())
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
    assert policy.last_diagnostics["rl_safety_filter_fallback_used"] is True
    assert policy.last_diagnostics["rl_safety_filter_reason"] == "checkpoint_missing"


def test_missing_prediction_fail_closed_returns_empty() -> None:
    policy = build_hybrid_policy(
        config=safety_config(fail_closed=True),
        prediction=unavailable_prediction("checkpoint_missing"),
    )

    assert policy.rank(request("closest"), candidates(), runtime_context={}) == []
```

- [ ] **Step 2: Write failing block-mode tests**

Add:

```python
def test_block_mode_removes_only_block_eligible_candidates() -> None:
    result = apply_safety_to_options(
        base_options=[option("safe", 0.6), option("unsafe", 0.9)],
        safety_by_station={
            "safe": candidate_safety(penalty=0.0, blocked=False),
            "unsafe": candidate_safety(penalty=0.8, blocked=True),
        },
        penalty_weight=0.25,
        mode="block",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["safe"]
    assert result.blocked_count == 1


def test_all_blocked_fail_open_restores_original_order() -> None:
    base = [option("first", 0.8), option("second", 0.7)]
    result = apply_safety_to_options(
        base_options=base,
        safety_by_station={
            "first": candidate_safety(penalty=1.0, blocked=True),
            "second": candidate_safety(penalty=1.0, blocked=True),
        },
        penalty_weight=0.25,
        mode="block",
        block_unsafe=False,
        fail_closed=False,
    )

    assert [item.station_id for item in result.options] == ["first", "second"]
    assert result.fallback_used is True
    assert result.reason == "all_candidates_blocked_fail_open"


def test_all_blocked_fail_closed_returns_empty() -> None:
    result = apply_safety_to_options(
        base_options=[option("only", 0.8)],
        safety_by_station={
            "only": candidate_safety(penalty=1.0, blocked=True),
        },
        penalty_weight=0.25,
        mode="block",
        block_unsafe=False,
        fail_closed=True,
    )

    assert result.options == ()
    assert result.fallback_used is False
```

- [ ] **Step 3: Write exact-only all-unmapped test**

Add:

```python
def test_exact_only_all_unmapped_is_not_applied() -> None:
    policy = build_hybrid_policy(
        config=safety_config(mapping_mode="exact_only"),
        prediction=available_prediction(0, "feeder-a"),
    )

    result = policy.rank(
        request("closest"),
        candidates("dundee-a", "dundee-b"),
        runtime_context=complete_context(
            feeder_station_ids=["feeder-a"],
            action_mask=[True],
        ),
    )

    assert [item.station_id for item in result] == closest_ids(
        candidates("dundee-a", "dundee-b")
    )
    assert all(item.metadata["rl_safety_penalty"] == 0.0 for item in result)
    assert all(item.metadata["rl_safety_status"] == "unmapped" for item in result)
    assert policy.last_diagnostics["rl_safety_filter_applied"] is False
```

- [ ] **Step 4: Implement candidate safety assembly**

Add:

```python
def build_candidate_safety(
    *,
    candidate_station_ids: Sequence[str],
    mappings: Mapping[str, CandidateFeederMapping],
    grid_advisories: Mapping[str, object],
    selected_feeder_station_id: str | None,
    shared_metadata: Mapping[str, Any],
) -> dict[str, CandidateSafety]:
    result: dict[str, CandidateSafety] = {}
    for candidate_id in candidate_station_ids:
        mapping = mappings[candidate_id]
        if mapping.feeder_station_id is None:
            result[candidate_id] = CandidateSafety(
                station_id=candidate_id,
                status="unmapped",
                score=1.0,
                penalty=0.0,
                reason="no_candidate_feeder_mapping",
                blocked=False,
                mapping=mapping,
                advisory=advisory_safety(None),
                metadata=_mapping_metadata(mapping, shared_metadata),
            )
            continue
        advisory = advisory_safety(
            grid_advisories.get(mapping.feeder_station_id)
        )
        selected = mapping.feeder_station_id == selected_feeder_station_id
        reason = (
            "checkpoint_selected_recorded_advisory"
            if selected
            else advisory.reason
        )
        result[candidate_id] = CandidateSafety(
            station_id=candidate_id,
            status=advisory.status,
            score=advisory.score,
            penalty=advisory.penalty,
            reason=reason,
            blocked=advisory.block_eligible,
            mapping=mapping,
            advisory=advisory,
            metadata={
                **_mapping_metadata(mapping, shared_metadata),
                "rl_selected_feeder_station_id": selected_feeder_station_id,
                "rl_selected_action_index": shared_metadata.get(
                    "rl_selected_action_index"
                ),
            },
        )
    return result
```

The selected action changes reason/diagnostics only. It does not lower a risky
recorded advisory penalty and never overrides `REJECT`, `VIOLATION`, or
OPF-infeasible facts.

- [ ] **Step 5: Implement unavailable-context behavior**

In hybrid `rank`, require:

```python
required_context = (
    "feeder_observation",
    "feeder_action_mask",
    "feeder_station_ids",
    "grid_advisories",
)
missing = [name for name in required_context if runtime_context.get(name) is None]
```

If missing:

- fail-open returns base options with `base_preference_score`,
  `rl_safety_adjusted_score=base_preference_score`,
  `rl_safety_status=unavailable`, and exact failure diagnostics;
- fail-closed returns `[]`.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_rl_safety_filter.py tests\recommender\test_rl_safety_policies.py -q
```

- [ ] **Step 7: Commit failure and block behavior**

```powershell
git add packages/ev_core/src/ev_core/recommender/rl_safety_filter.py tests/recommender/test_rl_safety_filter.py tests/recommender/test_rl_safety_policies.py
git commit -m "feat: add RL safety failure and block modes"
```

## Phase D: Registry, Runtime, Service Metadata, And Schema Preservation

### Task 8: Register Hybrid Policies Without Eager ML Imports

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/policy_registry.py`
- Modify: `tests/recommender/test_policy_registry.py`

- [ ] **Step 1: Write failing registry tests**

Add:

```python
def test_policy_registry_returns_all_rl_safety_policies() -> None:
    registry = PolicyRegistry()

    assert registry.get("rl_safety_closest").name == "rl_safety_closest"
    assert registry.get("rl_safety_cheapest").name == "rl_safety_cheapest"
    assert registry.get("rl_safety_fastest").name == "rl_safety_fastest"
    assert registry.get("rl_safety_weighted").name == "rl_safety_weighted"
    assert registry.get("rl_safety_preference").name == "rl_safety_preference"
```

Add a subprocess import guard:

```python
def test_policy_registry_import_does_not_import_optional_ml_packages() -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "import ev_core.recommender.policy_registry; "
            "assert 'torch' not in sys.modules; "
            "assert 'stable_baselines3' not in sys.modules; "
            "assert 'sb3_contrib' not in sys.modules"
        ),
    ]

    subprocess.run(command, check=True)
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_policy_registry.py -q
```

- [ ] **Step 3: Register hybrid classes**

Import the five wrapper classes. This is safe because
`FeederMaskablePPORuntimePolicy` imports sb3-contrib only inside `_load_model`.
Add all five names to `_policy_types`.

- [ ] **Step 4: Run and verify GREEN**

Expected: registry and import-laziness tests pass.

- [ ] **Step 5: Commit registration**

```powershell
git add packages/ev_core/src/ev_core/recommender/policy_registry.py tests/recommender/test_policy_registry.py
git commit -m "feat: register RL safety hybrid policies"
```

### Task 9: Build Feeder Context Only For Feeder-Aware Paths

**Files:**
- Modify: `packages/ev_core/src/ev_core/env/dundee_env.py`
- Modify: `tests/recommender/test_dundee_env_recommendation_policy.py`

- [ ] **Step 1: Write failing context-trigger tests**

Add:

```python
@pytest.mark.parametrize(
    "policy_name",
    [
        "rl_safety_closest",
        "rl_safety_cheapest",
        "rl_safety_fastest",
        "rl_safety_weighted",
        "rl_safety_preference",
    ],
)
def test_hybrid_policy_builds_feeder_context(monkeypatch, policy_name: str) -> None:
    seen = {"called": False}

    def fake_build(*args, **kwargs):
        seen["called"] = True
        return FeederRuntimeContextResult(
            runtime_context={"feeder_observation": [0.0]},
            metadata={"feeder_context_available": True},
            context_available=True,
        )

    monkeypatch.setattr(dundee_env_module, "build_feeder_runtime_context", fake_build)

    env = env_with_fake_service()
    env.get_ranked_recommendations(
        request(),
        recommendation_policy_name=policy_name,
        policy_selection_metadata={"preference_mode": "closest"},
    )

    assert seen["called"] is True


def test_normal_closest_does_not_build_feeder_context_when_safety_disabled(monkeypatch) -> None:
    monkeypatch.setattr(
        dundee_env_module,
        "build_feeder_runtime_context",
        lambda *args, **kwargs: pytest.fail("unexpected feeder context"),
    )

    env_with_fake_service().get_ranked_recommendations(
        request(),
        recommendation_policy_name="closest",
        policy_selection_metadata={"rl_safety_filter_enabled": False},
    )
```

- [ ] **Step 2: Write original-preference preservation test**

Assert `rl_safety_preference` passes the original request preference to
`RecommendationService`, not the hybrid policy name.

- [ ] **Step 3: Run and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_dundee_env_recommendation_policy.py -q
```

- [ ] **Step 4: Add feeder-aware policy helper**

In config or safety module expose:

```python
def policy_requires_feeder_context(
    policy_name: str | None,
    metadata: Mapping[str, Any] | None = None,
) -> bool:
    return bool(
        policy_name == FEEDER_POLICY_NAME
        or is_rl_safety_policy(policy_name)
        or (metadata or {}).get("rl_safety_filter_enabled")
    )
```

Use it in `DundeeEnv.get_ranked_recommendations`. Merge context metadata exactly
as the existing raw feeder path does. Pass safety selection metadata into
`runtime_context` so wrappers receive mode, weight, mapping mode, and strict
settings.

- [ ] **Step 5: Run and verify GREEN**

- [ ] **Step 6: Commit context routing**

```powershell
git add packages/ev_core/src/ev_core/env/dundee_env.py tests/recommender/test_dundee_env_recommendation_policy.py
git commit -m "feat: build feeder context for safety policies"
```

### Task 10: Merge Hybrid Diagnostics Into Response Metadata

**Files:**
- Modify: `packages/ev_core/src/ev_core/recommender/service.py`
- Modify: `tests/recommender/test_recommendation_service.py`

- [ ] **Step 1: Write failing response-diagnostic tests**

Use a fake policy with `last_diagnostics`:

```python
class DiagnosticPolicy:
    name = "rl_safety_closest"

    def __init__(self) -> None:
        self.last_diagnostics = {}

    def rank(self, request, candidates, runtime_context=None):
        option_value = candidate_to_option(candidates[0], score=0.5)
        self.last_diagnostics = {
            "final_ranker": "closest",
            "rl_safety_filter_enabled": True,
            "rl_safety_filter_applied": True,
            "rl_safety_filter_mode": "penalty",
            "rl_safety_mapping_mode": "exact_only",
            "rl_safety_candidates_penalized": 1,
            "rl_safety_candidates_blocked": 0,
            "rl_safety_filter_fallback_used": False,
            "rl_safety_filter_reason": "rl_safety_filter_applied",
            "fallback_used": False,
        }
        return [option_value]
```

Assert response metadata contains all keys and the response field set remains
exactly unchanged.

- [ ] **Step 2: Write forecast and dynamic-pricing preservation tests**

Pass existing forecast metadata in runtime context and candidate metadata with
`dynamic_pricing_enabled`, `final_price_per_kwh`, and tariff fields. Assert they
survive candidate and response assembly.

- [ ] **Step 3: Run and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_recommendation_service.py tests\recommender\test_forecast_metadata_integration.py -q
```

- [ ] **Step 4: Return internal ranking metadata**

Change private `_rank` to return:

```python
tuple[list[RecommendationOption], dict[str, Any]]
```

For named policies:

```python
policy = self.policy_registry.get(policy_name)
ranked = policy.rank(payload, candidate_contexts, runtime_context=runtime_context)
diagnostics = dict(getattr(policy, "last_diagnostics", {}) or {})
return ranked, diagnostics
```

Use equivalent logic for injected/default policies. This private change does
not alter public contracts.

- [ ] **Step 5: Merge diagnostics after forecast metadata**

In `recommend`, replace the current call with:

```python
ranked, ranking_metadata = self._rank(
    payload,
    candidate_contexts,
    runtime_context=runtime_context_payload,
    policy_name=policy_name,
)
metadata = dict(policy_selection_metadata or {})
metadata.update(forecast_metadata)
metadata.update(ranking_metadata)
```

Derive `dynamic_pricing_enabled` from the top option only when present:

```python
if ranked:
    top_metadata = dict(ranked[0].metadata or {})
    if "dynamic_pricing_enabled" in top_metadata:
        metadata["dynamic_pricing_enabled"] = top_metadata[
            "dynamic_pricing_enabled"
        ]
```

- [ ] **Step 6: Run and verify GREEN**

Expected: diagnostics, forecast, pricing, and unchanged-schema tests pass.

- [ ] **Step 7: Commit response metadata integration**

```powershell
git add packages/ev_core/src/ev_core/recommender/service.py tests/recommender/test_recommendation_service.py
git commit -m "feat: expose RL safety response diagnostics"
```

### Task 11: Propagate Safety Config Through Runtime And API Bootstrap

**Files:**
- Modify: `services/sim_runtime/runtime_manager.py`
- Modify: `apps/api/app/services/runtime_service.py`
- Modify: `tests/sim_runtime/test_runtime_recommendation_policy.py`
- Modify: `tests/api/test_runtime_service_recommendation_policy_config.py`

- [ ] **Step 1: Write failing runtime-config propagation tests**

Assert all six safety fields in `RuntimeConfig`, runtime status, and
policy-selection metadata.

Add:

```python
def test_runtime_service_passes_rl_safety_config(monkeypatch) -> None:
    monkeypatch.setenv("RL_SAFETY_FILTER_ENABLED", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_MODE", "penalty")
    monkeypatch.setenv("RL_SAFETY_FILTER_STRICT", "true")
    monkeypatch.setenv("RL_SAFETY_FILTER_PENALTY_WEIGHT", "0.5")
    monkeypatch.setenv("RL_SAFETY_BLOCK_UNSAFE", "false")
    monkeypatch.setenv(
        "RL_SAFETY_MAPPING_MODE",
        "stable_ordinal_demo_bridge",
    )

    manager = runtime_service.get_runtime_manager()

    assert manager.config.rl_safety_filter_enabled is True
    assert manager.config.rl_safety_filter_penalty_weight == 0.5
    assert manager.config.rl_safety_mapping_mode == "stable_ordinal_demo_bridge"
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\api\test_runtime_service_recommendation_policy_config.py tests\sim_runtime\test_runtime_recommendation_policy.py -q
```

- [ ] **Step 3: Extend `RuntimeConfig`**

Add the same six fields and defaults as `RecommendationConfig`.

Add them to:

- `_compose_runtime_status`;
- `_policy_selection_metadata`.

Do not independently re-resolve policy names in the manager. Continue using the
effective name selected by config/API precedence.

- [ ] **Step 4: Populate from runtime service**

Map every field from `recommendation_cfg` into `RuntimeConfig`.

No changes are required in `apps/api/app/services/recommendations_service.py`
unless tests reveal missing metadata, because it already uses
`select_recommendation_policy`.

- [ ] **Step 5: Run and verify GREEN**

- [ ] **Step 6: Commit runtime propagation**

```powershell
git add services/sim_runtime/runtime_manager.py apps/api/app/services/runtime_service.py tests/sim_runtime/test_runtime_recommendation_policy.py tests/api/test_runtime_service_recommendation_policy_config.py
git commit -m "feat: propagate RL safety runtime config"
```

## Phase E: Verification Script

### Task 12: Add The Hybrid Preference Verifier

**Files:**
- Create: `scripts/verification/verify_rl_safety_preference_ranking.py`
- Create or modify: `tests/verification/test_rl_safety_preference_ranking.py`

- [ ] **Step 1: Write failing verifier helper tests**

Test pure verifier assertions with synthetic responses:

```python
def test_compare_baseline_and_hybrid_preserves_raw_fields() -> None:
    result = compare_baseline_and_hybrid(
        baseline_response=baseline_response(),
        hybrid_response=hybrid_response(),
        expected_final_ranker="cheapest",
    )

    assert result["schema_unchanged"] is True
    assert result["raw_fields_unchanged"] is True
    assert result["final_ranker_preserved"] is True
```

Add strict failure tests for fallback, missing safety metadata, changed raw
fields, or bridge metadata claiming physical identity.

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\verification\test_rl_safety_preference_ranking.py -q
```

- [ ] **Step 3: Implement verifier CLI and result contract**

Support:

```text
--strict
--mapping-mode exact_only|stable_ordinal_demo_bridge
--penalty-weight
```

Run baseline/hybrid pairs:

```python
POLICY_CASES = (
    ("closest", "rl_safety_closest"),
    ("cheapest", "rl_safety_cheapest"),
    ("fastest", "rl_safety_fastest"),
    ("weighted_score", "rl_safety_weighted"),
)
```

Also run `rl_safety_preference` for closest, cheapest, and fastest requests.

- [ ] **Step 4: Verify required runtime properties**

For each pair record:

- response field names;
- final ranker;
- station order;
- raw candidate fields;
- pricing metadata;
- base and adjusted scores;
- safety metadata;
- fallback status;
- mapping kind and physical-claim flag.

Use controlled synthetic policy/filter calls for:

- penalty weight zero;
- all penalties zero;
- risky candidate demotion;
- exact-only unmatched behavior;
- stable bridge determinism;
- block mode;
- all-blocked fail-open and fail-closed.

In artifact-complete strict mode, run real checkpoint inference and require:

```text
fallback_used=false
rl_safety_filter_fallback_used=false
```

- [ ] **Step 5: Emit machine-readable output**

Print JSON with:

```python
{
    "strict": args.strict,
    "policy_cases": case_results,
    "synthetic_safety_cases": synthetic_results,
    "checkpoint_observation_shape": observation_shape,
    "checkpoint_action_count": action_count,
    "fallback_used": fallback_used,
    "limitations": [
        "offline recorded feeder context",
        "stable ordinal bridge is nonphysical app/demo mapping",
        "primary grid-performance evidence remains feeder evaluator evidence",
    ],
}
```

Return nonzero in strict mode only for operational/contract failures.

- [ ] **Step 6: Run helper tests and commit**

```powershell
git add scripts/verification/verify_rl_safety_preference_ranking.py tests/verification/test_rl_safety_preference_ranking.py
git commit -m "test: verify RL safety preference ranking"
```

## Phase F: Documentation And Environment Example

### Task 13: Document Hybrid Architecture And Evidence Boundary

**Files:**
- Modify: `docs/ai_context/RECOMMENDER_FLOW.md`
- Modify: `docs/ai_context/REQUEST_FLOW.md`
- Modify: `docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md`
- Modify: `docs/ai_context/RL_READINESS_REPORT.md`
- Modify: `docs/ai_context/RUNTIME_ARTIFACTS_AND_MODEL_LOADING.md`
- Modify: `docs/ai_context/OPEN_QUESTIONS.md`
- Modify: `docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md`
- Modify: `docs/ev_side/OFFLINE_FEEDER_RL_FORECASTING_PR_PLAN.md`
- Modify: `.env.feeder_rl_demo.example`

- [ ] **Step 1: Update architecture documentation**

Add the exact flow:

```text
app candidate construction with dynamic pricing
-> optional feeder runtime context and checkpoint prediction
-> exact or explicitly nonphysical demo mapping
-> bounded safety penalty/blocking
-> existing deterministic preference ranker order adjusted by safety
-> unchanged response schema
```

State repeatedly:

- deterministic preference ranking remains default;
- the checkpoint is not preference-conditioned;
- cheapest still uses dynamic `estimated_cost_gbp`;
- weighted still uses its existing formula;
- forecast metadata is not fed into RL;
- stable ordinal mapping is nonphysical app/demo evidence only;
- it cannot support primary grid-performance claims;
- primary grid-performance evidence remains feeder-evaluator evidence;
- PR 6.1 remains paused infrastructure;
- PR 6.3 is future hybrid evidence scope.

- [ ] **Step 2: Update the environment example**

Add:

```env
# Conservative default: deterministic preference ranking only
RL_SAFETY_FILTER_ENABLED=false
RL_SAFETY_MAPPING_MODE=exact_only

# Hybrid RL safety filter + user preference final ranker
RECOMMENDATION_POLICY_NAME=rl_safety_preference
RL_SAFETY_FILTER_ENABLED=true
RL_SAFETY_FILTER_MODE=penalty
RL_SAFETY_FILTER_STRICT=false
RL_SAFETY_BLOCK_UNSAFE=false
RL_SAFETY_FILTER_PENALTY_WEIGHT=0.25
RL_SAFETY_MAPPING_MODE=stable_ordinal_demo_bridge
RL_FEEDER_CHECKPOINT_PATH=models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip
FEEDER_RL_DATA_DIR=data/processed/evside_feeder_rl
GRID_ADVISORY_MODE=recorded
GRID_ADVISORY_REPLAY_DIR=data/processed/evside_feeder_rl
RL_POLICY_FAIL_CLOSED=false
```

Add a comment that the bridge does not claim physical station identity.

- [ ] **Step 3: Verify documentation references**

Run:

```powershell
rg -n "rl_safety_preference|stable_ordinal_demo_bridge|nonphysical_demo_mapping|primary grid-performance" docs .env.feeder_rl_demo.example
```

Expected: all requested docs and the environment example contain the relevant
architecture/evidence wording.

- [ ] **Step 4: Commit documentation**

```powershell
git add docs/ai_context/RECOMMENDER_FLOW.md docs/ai_context/REQUEST_FLOW.md docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md docs/ai_context/RL_READINESS_REPORT.md docs/ai_context/RUNTIME_ARTIFACTS_AND_MODEL_LOADING.md docs/ai_context/OPEN_QUESTIONS.md docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md docs/ev_side/OFFLINE_FEEDER_RL_FORECASTING_PR_PLAN.md .env.feeder_rl_demo.example
git commit -m "docs: document RL safety preference ranking"
```

## Phase G: Full Verification Matrix

### Task 14: Run Focused, Integration, And Regression Verification

**Files:**
- No code changes unless a failure is first reproduced by a focused failing test.

- [ ] **Step 1: Run pure and focused safety tests**

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests\recommender\test_rl_safety_filter.py tests\recommender\test_rl_safety_policies.py tests\verification\test_rl_safety_preference_ranking.py -q
```

Expected: all pass without requiring optional ML packages for pure/fake-model
cases.

- [ ] **Step 2: Run focused recommender/API/runtime tests**

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests\recommender tests\api tests\sim_runtime -q
```

Expected: all pass; existing deterministic behavior remains unchanged.

- [ ] **Step 3: Run hybrid verifier**

```powershell
uv run --with pyarrow --with pydantic --with numpy --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\verify_rl_safety_preference_ranking.py --strict
```

Expected:

- all four explicit baseline/hybrid pairs pass;
- generic policy preserves closest/cheapest/fastest;
- response schema unchanged;
- dynamic pricing metadata present;
- raw fields unchanged;
- strict checkpoint fallback false;
- stable bridge labeled nonphysical;
- controlled safety cases pass.

- [ ] **Step 4: Run PR 4 no-fallback verifier**

```powershell
uv run --with pyarrow --with pydantic --with numpy --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\verify_feeder_rl_api_no_fallback.py --strict
```

Expected: passes with `fallback_used=false`, observation shape `[2200]`, and 73
actions.

- [ ] **Step 5: Run PR 5 forecast verifier**

```powershell
uv run --with pydantic --with numpy --with pandas --with joblib --with tensorflow --with scikit-learn python scripts\verification\verify_forecasting_provider.py --provider keras_load_kw_30min --model-dir models\forecasting\load_kw_30min --strict --allow-smoke-template
```

Expected: provider smoke passes and remains metadata-only.

- [ ] **Step 6: Run full tests**

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests -q
```

Expected: full suite passes.

- [ ] **Step 7: Check forbidden changes and diff quality**

```powershell
git diff --check
git status --short
git diff --name-only
```

Confirm no changes under:

- `packages/ev_core/src/ev_core/contracts/requests.py`
- `packages/ev_core/src/ev_core/contracts/responses.py`
- `packages/ev_core/src/ev_core/rl_feeder/observations.py`
- `packages/ev_core/src/ev_core/rl_feeder/rewards.py`
- `models/`
- PR 6.1 plan/spec files.

- [ ] **Step 8: Commit final integration fixes**

Only if verification produced test-first fixes:

```powershell
git add packages/ev_core/src/ev_core/config/recommendation.py packages/ev_core/src/ev_core/recommender/rl_safety_filter.py packages/ev_core/src/ev_core/recommender/feeder_rl_policy.py packages/ev_core/src/ev_core/recommender/policy_registry.py packages/ev_core/src/ev_core/recommender/service.py packages/ev_core/src/ev_core/env/dundee_env.py services/sim_runtime/runtime_manager.py apps/api/app/services/runtime_service.py scripts/verification/verify_rl_safety_preference_ranking.py tests/config/test_routing_pricing_recommendation_config.py tests/recommender/test_rl_safety_filter.py tests/recommender/test_rl_safety_policies.py tests/recommender/test_policy_registry.py tests/recommender/test_feeder_rl_policy_diagnostics.py tests/recommender/test_recommendation_service.py tests/recommender/test_dundee_env_recommendation_policy.py tests/api/test_app_recommendation_mapping.py tests/api/test_runtime_service_recommendation_policy_config.py tests/sim_runtime/test_runtime_recommendation_policy.py tests/verification/test_rl_safety_preference_ranking.py
git commit -m "feat: add RL safety preference ranking"
```

## Acceptance Criteria

Implementation is complete only when:

- all five hybrid policies are registered;
- explicit hybrid policies self-enable;
- automatic safety configuration maps deterministic policies to corresponding
  hybrid policies;
- default deterministic policies remain behaviorally unchanged;
- hybrid policies wrap existing rankers and do not duplicate their formulas;
- penalty mode uses
  `adjusted_score = base_preference_score - penalty_weight * safety_penalty`;
- safety penalty and weight remain within `[0.0, 1.0]`;
- higher adjusted scores rank earlier;
- stable sorting preserves deterministic order for equal adjusted scores;
- penalty mode retains every option;
- raw distance, cost, duration, wait, pricing, queue, utilization, headroom,
  compatibility, and identity fields remain unchanged;
- block mode removes only configured unsafe candidates;
- all-blocked fail-open restores deterministic ranking with diagnostics;
- all-blocked fail-closed returns controlled no-option behavior;
- fail-closed never silently returns deterministic recommendations;
- exact ID/documented mapping takes precedence;
- exact-only unmatched candidates remain unpenalized;
- exact-only all-unmapped results are marked not applied;
- stable ordinal bridge is deterministic over sorted identifiers;
- persistent mapping does not use Python `hash()`;
- ordinal bridge metadata is explicitly nonphysical;
- ordinal bridge is described only as app/demo evidence;
- primary grid-performance evidence remains feeder-evaluator evidence;
- candidate metadata includes base and adjusted scores plus all required safety,
  mapping, feeder, provenance, and fallback diagnostics;
- response diagnostics are present in existing metadata only;
- response schema field names remain unchanged;
- dynamic pricing remains active and cheapest still uses dynamic estimated cost;
- forecast metadata remains unchanged and is not fed into RL;
- missing optional dependencies do not affect default startup;
- policy-registry import does not import Torch/SB3/sb3-contrib;
- hybrid verifier passes;
- PR 4 no-fallback verifier passes;
- PR 5 forecast verifier passes;
- focused and full tests pass;
- docs and environment example are updated;
- no schema, checkpoint, observation, reward, live-control, MARL, PR 6.1, or
  PR 6.3 implementation changes are introduced.

## Final Response Requirements

The future implementation response must summarize:

- files changed;
- new hybrid policies and configuration;
- how feeder RL safety filtering works;
- candidate-to-feeder mapping precedence;
- exact mapping versus stable ordinal bridge labeling;
- how each preference ranker is preserved;
- penalty and block behavior;
- dynamic pricing status;
- hybrid verifier results;
- focused and full test results;
- PR 4 no-fallback verifier result;
- PR 5 forecast verifier result;
- remaining limitations;
- next recommended PR: PR 6.3 hybrid thesis benchmark and feeder-evaluator
  evidence export.
