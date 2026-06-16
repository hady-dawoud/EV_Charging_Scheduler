# Feeder RL Thesis Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, thesis-grade feeder RL evaluation exporter that compares random, weighted, and checkpoint policies on identical replay-backed request sets, transparently searches valid configurations, and exports honest statistics, reports, claims, and figures.

**Architecture:** Start with one import-safe verification script containing focused dataclasses and pure helpers, plus one focused test file. Keep feeder evaluation direct through `FeederStationSelectionEnv`; isolate secondary app cost evidence behind a dedicated adapter and output directory. Extract production modules only if the single-script boundary becomes materially hard to test.

**Tech Stack:** Python 3.10+, dataclasses, pandas, NumPy, Gymnasium, PyTorch, Stable-Baselines3, sb3-contrib, Pydantic, Matplotlib, pytest.

---

## File Structure

- Create: `scripts/verification/export_feeder_rl_thesis_evaluation.py`
  - Owns CLI parsing, mode/scenario definitions, deterministic request generation, feeder evaluation, aggregation, search, optional secondary app cost evidence, strict validation, reports, and figures.
- Create: `tests/verification/test_feeder_rl_thesis_evaluation.py`
  - Covers pure helpers with synthetic rows first, then fake-environment integration and artifact contracts.
- Modify: `docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md`
  - Distinguishes the original app smoke benchmark from the new primary feeder performance evaluator.
- Modify: `scripts/verification/README.md`
  - Documents the new command, output directory, and evidence boundary.
- Do not modify:
  - `packages/ev_core/src/ev_core/rl_feeder/env.py`
  - `packages/ev_core/src/ev_core/rl_feeder/rewards.py`
  - `packages/ev_core/src/ev_core/rl_feeder/observations.py`
  - checkpoint files or app/API/mobile schemas.

## Phase A: Pure Helpers And Synthetic Tests

### Task 1: Define Modes, Scenarios, And Deterministic Request Transformations

**Files:**
- Create: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Create: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing contract tests**

Add these tests:

```python
from __future__ import annotations

from datetime import datetime, timedelta

from ev_core.rl_feeder.contracts import FeederRequest


def _request(index: int = 1) -> FeederRequest:
    arrival = datetime(2024, 6, 10, 12, 0) + timedelta(minutes=15 * index)
    return FeederRequest(
        request_id=f"req-{index}",
        secondary_area_id="area-a",
        arrival_timestamp=arrival,
        latest_finish_timestamp=arrival + timedelta(hours=3),
        requested_energy_kwh=18.0,
        battery_kwh=60.0,
        current_soc=0.30,
        target_soc=0.80,
        charger_type_preference="ac",
        max_ac_kw=22.0,
        max_dc_kw=50.0,
        origin_x=100.0,
        origin_y=200.0,
    )


def test_mode_defaults_meet_request_minimums() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import MODE_SPECS

    assert MODE_SPECS["quick"].seed_count == 10
    assert MODE_SPECS["quick"].total_requests == 160
    assert MODE_SPECS["thesis"].seed_count == 50
    assert MODE_SPECS["thesis"].total_requests == 800
    assert MODE_SPECS["stress"].seed_count == 90
    assert MODE_SPECS["stress"].total_requests == 2160


def test_scenario_matrix_has_required_order() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import build_scenario_matrix

    assert [item.name for item in build_scenario_matrix()] == [
        "normal_replay",
        "evening_peak",
        "high_demand",
        "deadline_pressure",
        "low_soc_urgent",
        "constrained_replay_area",
        "grid_stress_heavy",
        "mixed_service_cost",
    ]


def test_transform_requests_is_deterministic_and_does_not_mutate_input() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import (
        build_scenario_matrix,
        transform_requests,
    )

    original = [_request()]
    scenario = next(item for item in build_scenario_matrix() if item.name == "high_demand")
    first = transform_requests(original, scenario=scenario, stress_profile="standard")
    second = transform_requests(original, scenario=scenario, stress_profile="standard")

    assert first == second
    assert original[0].requested_energy_kwh == 18.0
    assert first[0].requested_energy_kwh > original[0].requested_energy_kwh
    assert 0.0 <= first[0].current_soc < first[0].target_soc <= 1.0
    assert first[0].latest_finish_timestamp > first[0].arrival_timestamp


def test_request_fingerprint_changes_when_request_set_changes() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import request_set_fingerprint

    first = request_set_fingerprint([_request(1)])
    second = request_set_fingerprint([_request(2)])

    assert first != second
    assert first == request_set_fingerprint([_request(1)])
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests\verification\test_feeder_rl_thesis_evaluation.py -q
```

Expected: FAIL because `export_feeder_rl_thesis_evaluation` does not exist.

- [ ] **Step 3: Add minimal import-safe mode and scenario helpers**

Create the script with standard-library imports at module import time and these
public contracts:

```python
@dataclass(frozen=True)
class ModeSpec:
    seed_count: int
    requests_per_scenario: int
    minimum_requests: int
    scenario_count: int = 8

    @property
    def total_requests(self) -> int:
        return self.seed_count * self.requests_per_scenario * self.scenario_count


MODE_SPECS = {
    "quick": ModeSpec(seed_count=10, requests_per_scenario=2, minimum_requests=150),
    "thesis": ModeSpec(seed_count=50, requests_per_scenario=2, minimum_requests=750),
    "stress": ModeSpec(seed_count=90, requests_per_scenario=3, minimum_requests=1500),
}


@dataclass(frozen=True)
class ScenarioSpec:
    name: str
    hour: int
    energy_multiplier: float = 1.0
    soc_cap: float | None = None
    deadline_minutes: int | None = None
    area_strategy: str = "balanced"


def build_scenario_matrix() -> list[ScenarioSpec]:
    return [
        ScenarioSpec("normal_replay", 12),
        ScenarioSpec("evening_peak", 18),
        ScenarioSpec("high_demand", 17, energy_multiplier=1.8, soc_cap=0.25),
        ScenarioSpec("deadline_pressure", 9, deadline_minutes=60),
        ScenarioSpec("low_soc_urgent", 14, energy_multiplier=1.6, soc_cap=0.15, deadline_minutes=90),
        ScenarioSpec("constrained_replay_area", 16, area_strategy="few_valid_actions"),
        ScenarioSpec("grid_stress_heavy", 18, energy_multiplier=1.5, area_strategy="highest_replay_stress"),
        ScenarioSpec("mixed_service_cost", 11),
    ]
```

Implement `transform_requests(...)` with `dataclasses.replace`, preserving
request IDs and feeder areas while changing only valid request fields. Implement
`request_set_fingerprint(...)` by serializing all request dataclass fields in
stable order and hashing with SHA-256.

- [ ] **Step 4: Run tests and verify GREEN**

Run the focused command again.

Expected: `4 passed`.

- [ ] **Step 5: Commit Phase A scenario contracts**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "test: define feeder thesis evaluation scenarios"
```

### Task 2: Add Statistics, Comparisons, Composite Score, And Claim Guard

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing synthetic metric tests**

Add:

```python
def _episode_row(policy: str, seed: int, **overrides):
    row = {
        "policy": policy,
        "seed": seed,
        "scenario": "normal_replay",
        "target_feeder_area": "area-a",
        "total_requests": 2,
        "total_steps": 2,
        "served_requests": 2,
        "missed_requests": 0,
        "served_rate": 1.0,
        "missed_rate": 0.0,
        "invalid_actions": 0,
        "fallback_actions": 0,
        "total_reward": 2.0,
        "mean_reward": 1.0,
        "average_stress_score": 0.2,
        "max_stress_score": 0.3,
        "voltage_violation_count": 1,
        "line_overload_count": 1,
        "transformer_overload_count": 1,
        "opf_infeasible_count": 1,
        "mean_curtailment_required_kw": 2.0,
        "total_curtailment_required_kw": 4.0,
        "mean_feasible_energy_kwh": 16.0,
        "total_feasible_energy_kwh": 32.0,
        "truth_level_counts": {"area_pf": 2},
        "label_source_counts": {"area_reuse": 2},
        "average_valid_action_count": 4.0,
        "min_valid_action_count": 4,
        "selected_action_distribution": {"station-a": 2},
    }
    row.update(overrides)
    return row


def test_numeric_summary_includes_95_percent_confidence_interval() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import numeric_summary

    result = numeric_summary([1.0, 2.0, 3.0])

    assert result["count"] == 3
    assert result["mean"] == 2.0
    assert result["median"] == 2.0
    assert result["ci95_low"] < 2.0 < result["ci95_high"]


def test_core_grid_wins_count_strict_improvements_only() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import compare_checkpoint

    rows = [
        _episode_row("random", 1),
        _episode_row(
            "checkpoint",
            1,
            average_stress_score=0.1,
            voltage_violation_count=0,
            line_overload_count=0,
            transformer_overload_count=1,
            opf_infeasible_count=0,
            mean_curtailment_required_kw=1.0,
        ),
        _episode_row("weighted", 1, average_stress_score=0.05),
    ]

    comparison = compare_checkpoint(rows)

    assert comparison["vs_random"]["core_grid_wins"] == 5
    assert comparison["vs_random"]["target_met"] is True
    assert comparison["vs_weighted"]["average_stress_score"]["checkpoint_better"] is False


def test_zero_baseline_percent_is_unavailable() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import percent_improvement

    assert percent_improvement(0.0, 0.0, lower_is_better=True) is None
    assert percent_improvement(0.0, 1.0, lower_is_better=True) is None


def test_composite_score_does_not_use_secondary_app_cost() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import thesis_composite_score

    base = thesis_composite_score(
        random_metrics={"average_stress_score": 0.4, "served_rate": 0.8},
        checkpoint_metrics={"average_stress_score": 0.2, "served_rate": 0.9},
    )
    repeated = thesis_composite_score(
        random_metrics={"average_stress_score": 0.4, "served_rate": 0.8},
        checkpoint_metrics={"average_stress_score": 0.2, "served_rate": 0.9},
        secondary_cost_context={"checkpoint_cost": 1000.0, "cheapest_cost": 1.0},
    )

    assert base == repeated
    assert base["cost_score"] == 0.0


def test_claim_summary_is_never_blank_and_has_one_category() -> None:
    from scripts.verification.export_feeder_rl_thesis_evaluation import build_thesis_claims

    for wins in (5, 2, 0):
        result = build_thesis_claims(
            {
                "total_unique_requests": 160,
                "comparison": {
                    "vs_random": {"core_grid_wins": wins, "target_met": wins >= 4},
                    "vs_weighted": {},
                },
            }
        )
        categories = [
            heading for heading in ("Strong Supported Claim", "Balanced Claim", "Negative / Unmet-Target Claim")
            if heading in result
        ]
        assert len(categories) == 1
        assert result.strip()
```

- [ ] **Step 2: Run and verify RED**

Expected: failures for missing aggregation and claim helpers.

- [ ] **Step 3: Implement pure metric helpers**

Add:

```python
CORE_GRID_METRICS = (
    "average_stress_score",
    "voltage_violation_count",
    "line_overload_count",
    "transformer_overload_count",
    "opf_infeasible_count",
    "mean_curtailment_required_kw",
)


def numeric_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {"count": 0, "mean": None, "std": None, "median": None, "min": None, "max": None, "ci95_low": None, "ci95_high": None}
    mean = statistics.fmean(clean)
    std = statistics.stdev(clean) if len(clean) > 1 else 0.0
    margin = 1.96 * std / math.sqrt(len(clean))
    return {
        "count": len(clean),
        "mean": mean,
        "std": std,
        "median": statistics.median(clean),
        "min": min(clean),
        "max": max(clean),
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
    }


def percent_improvement(baseline: float, candidate: float, *, lower_is_better: bool) -> float | None:
    baseline = float(baseline)
    candidate = float(candidate)
    if abs(baseline) < 1e-12:
        return None
    delta = baseline - candidate if lower_is_better else candidate - baseline
    return 100.0 * delta / abs(baseline)
```

Implement `aggregate_policy_metrics`, `compare_checkpoint`,
`thesis_composite_score`, and `build_thesis_claims`. Bound each normalized
composite component to `[-1, 1]`. Keep `cost_score=0.0` in the primary
composite regardless of secondary app inputs.

Claim selection rules:

```python
if target_met:
    category = "Strong Supported Claim"
elif core_grid_wins > 0:
    category = "Balanced Claim"
else:
    category = "Negative / Unmet-Target Claim"
```

Always include the offline `area_pf` / `area_reuse` limitation and weighted
oracle-like comparator wording.

- [ ] **Step 4: Run and verify GREEN**

Expected: all Phase A tests pass.

- [ ] **Step 5: Commit pure metric helpers**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: add feeder thesis metric helpers"
```

## Phase B: Exporter Scaffold And Output Files

### Task 3: Export Synthetic Evidence Contracts Before Real Evaluation

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing artifact tests**

Add a test that calls `export_evidence_artifacts(...)` with three synthetic
policy rows and asserts these unconditional files:

```python
required = [
    "feeder_eval_results.csv",
    "feeder_eval_results.json",
    "per_seed_metrics.csv",
    "per_scenario_metrics.csv",
    "summary_metrics.json",
    "statistical_summary.json",
    "scenario_config.json",
    "run_metadata.json",
    "thesis_feeder_rl_evaluation_report.md",
    "thesis_claims_safe_summary.md",
]
for name in required:
    assert (tmp_path / name).is_file()

claims = (tmp_path / "thesis_claims_safe_summary.md").read_text(encoding="utf-8")
assert any(
    heading in claims
    for heading in ("Strong Supported Claim", "Balanced Claim", "Negative / Unmet-Target Claim")
)
assert not (tmp_path / "cost_service_summary.json").exists()
```

Add a second test with `cost_service_summary={"available": True, ...}` and
assert that `cost_service_summary.json` exists.

- [ ] **Step 2: Run and verify RED**

Expected: missing `export_evidence_artifacts`.

- [ ] **Step 3: Implement serialization and scaffold reports**

Add `_write_json`, `_write_csv`, `_jsonable_row`, and:

```python
def export_evidence_artifacts(
    *,
    output_dir: Path,
    rows: Sequence[Mapping[str, Any]],
    summary_metrics: Mapping[str, Any],
    statistical_summary: Mapping[str, Any],
    scenario_config: Mapping[str, Any],
    run_metadata: Mapping[str, Any],
    cost_service_summary: Mapping[str, Any] | None = None,
) -> dict[str, Path]:
    ...
```

CSV serialization must encode dict/list fields as JSON strings. Markdown
scaffolds must already state:

- feeder evaluator metrics are primary;
- app/runtime evidence is secondary;
- app success rate is not a feeder performance metric;
- weighted is a strong greedy grid-aware comparator.

- [ ] **Step 4: Add strict output validation**

Implement:

```python
def validate_exported_artifacts(
    output_dir: Path,
    *,
    require_cost: bool = False,
    require_figures: bool = False,
) -> list[str]:
    ...
```

Return error strings for missing files, empty CSVs, unparsable JSON, blank
claims, or claims with zero/multiple headline categories. Do not raise inside
the helper; the CLI strict layer raises after collecting all diagnostics.

- [ ] **Step 5: Run focused tests and commit**

Expected: artifact tests pass without Gymnasium, Torch, or SB3 imports.

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: scaffold feeder thesis evidence export"
```

## Phase C: Real Feeder Evaluator Integration

### Task 4: Freeze Identical Requests Across Policies

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write a failing fake-environment fairness test**

Define a fake environment that records the request IDs supplied to each policy
and call `evaluate_policy_matrix(...)`. Assert:

```python
assert result.request_fingerprints == {
    "random": result.request_fingerprints["checkpoint"],
    "weighted": result.request_fingerprints["checkpoint"],
    "checkpoint": result.request_fingerprints["checkpoint"],
}
assert set(result.rows_by_policy) == {"random", "weighted", "checkpoint"}
```

Also assert each policy sees the same scenario ID, area, request count, and
request ordering.

- [ ] **Step 2: Run and verify RED**

Expected: missing frozen generator and policy-matrix evaluator.

- [ ] **Step 3: Implement immutable request replay adapter**

Add:

```python
class FrozenRequestGenerator:
    def __init__(self, requests: Sequence[FeederRequest]) -> None:
        self._requests = tuple(requests)

    def generate_for_scenario(self, scenario: FeederEpisodeScenario) -> list[FeederRequest]:
        del scenario
        return list(self._requests)
```

Build base requests once with `FeederRequestGenerator`, then apply scenario
transformations once. Pass a new `FrozenRequestGenerator` instance into each
policy environment.

- [ ] **Step 4: Implement replay-area profiling**

Using the loaded replay frame and action catalog, compute:

- action count per feeder area;
- replay row count per feeder area;
- mean/max stress;
- violation and overload totals;
- truth-level and label-source counts.

Area strategies:

```python
def select_area_id(profile, *, scenario, seed):
    if scenario.area_strategy == "few_valid_actions":
        return sorted(profile, key=lambda item: (item.action_count, item.area_id))[seed % len(profile)].area_id
    if scenario.area_strategy == "highest_replay_stress":
        return sorted(profile, key=lambda item: (-item.mean_stress, item.area_id))[seed % len(profile)].area_id
    return sorted(profile, key=lambda item: item.area_id)[seed % len(profile)].area_id
```

Filter profiles to `area_pf` or stronger and exclude adapter proxies.

- [ ] **Step 5: Run fairness tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: freeze feeder requests across policies"
```

### Task 5: Run Random, Weighted, And Checkpoint Episodes

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing episode metric tests**

Use a fake environment with:

- one served request;
- one request with no valid actions;
- selected advisory provenance;
- deterministic action masks.

Assert exact totals for served/missed, rewards, stress, violations, overloads,
OPF infeasibility, curtailment, feasible energy, valid-action counts, truth
levels, label sources, and selected station distribution.

- [ ] **Step 2: Run and verify RED**

Expected: missing `evaluate_episode`.

- [ ] **Step 3: Implement policy action selection**

Add:

```python
def select_action(*, policy, env, model, observation, mask, rng) -> tuple[int, bool]:
    valid = [index for index, allowed in enumerate(mask) if allowed]
    if not valid:
        return 0, False
    if policy == "random":
        return valid[rng.randrange(len(valid))], False
    if policy == "weighted":
        scores = []
        for index in valid:
            action = env.actions[index]
            advisory = env.current_grid_advisories.get(action.station_id)
            score = env.reward_model.compute(
                selected_action=action,
                request=env.current_request,
                grid_advisory=advisory,
            ).total
            scores.append((float(score), -index, index))
        return max(scores)[2], False
    predicted, _ = model.predict(observation, deterministic=True, action_masks=mask)
    predicted = int(predicted)
    if predicted not in valid:
        return valid[rng.randrange(len(valid))], True
    return predicted, False
```

The weighted tie-break selects the lowest action index through the `-index`
secondary key.

- [ ] **Step 4: Implement full episode collection**

Before each `env.step`, retain the current request and valid count. After the
step, collect:

- selected station/action;
- selected advisory;
- reward and reward breakdown;
- missed/invalid/fallback;
- stress and all grid counts;
- curtailment and feasible energy;
- truth level and label source.

Compute feeder duration from actual selected charger power:

```python
duration_minutes = 60.0 * request.requested_energy_kwh / max(selected_action.charger_kw, 1.0)
```

Compute feeder distance only when both request and action coordinate systems
match. Direct feeder cost is available only when action metadata contains one
of:

```python
("price_per_kwh", "tariff_gbp_per_kwh", "cost_per_kwh_gbp")
```

Never invent a tariff. Missing price produces `None`.

- [ ] **Step 5: Load runtime dependencies lazily**

Inside runtime functions only:

```python
from ev_core.rl_feeder.env import FeederStationSelectionEnv
from sb3_contrib import MaskablePPO
```

Load the checkpoint once per benchmark process. Validate detected model
observation shape against `env.observation_space.shape`, which must remain
`(2200,)` for the installed 73-action package.

- [ ] **Step 6: Run focused tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: evaluate feeder policies with replay metrics"
```

### Task 6: Aggregate Seed, Scenario, Statistical, And Cost-Service Metrics

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing aggregation tests**

Assert:

- `per_seed_metrics.csv` groups by policy and seed across scenarios;
- `per_scenario_metrics.csv` groups by policy and scenario across seeds;
- statistical summary contains mean/std/median/min/max/CI;
- checkpoint reward recovery versus weighted is calculated;
- direct feeder cost appears only when every contributing row has genuine
  price-derived cost;
- missing direct cost yields `{"available": False, "source": "unavailable"}`.

- [ ] **Step 2: Implement grouped aggregation**

Use explicit metric direction maps:

```python
LOWER_IS_BETTER = {
    "average_stress_score",
    "voltage_violation_count",
    "line_overload_count",
    "transformer_overload_count",
    "opf_infeasible_count",
    "mean_curtailment_required_kw",
    "invalid_actions",
    "fallback_actions",
}

HIGHER_IS_BETTER = {
    "total_reward",
    "mean_reward",
    "served_rate",
    "mean_feasible_energy_kwh",
}
```

Generate `summary_metrics.json` with:

- selected policy aggregates;
- checkpoint vs random;
- checkpoint vs weighted;
- core win count and target status;
- composite components;
- direct feeder cost availability;
- total unique request count;
- total policy evaluation row count.

- [ ] **Step 3: Run focused tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: aggregate feeder thesis statistics"
```

## Phase D: Transparent Search

### Task 7: Export Every Search Attempt And Select Deterministically

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing search selection tests**

Create synthetic search runs and assert:

```python
selected = select_search_run(
    [
        {"run_number": 1, "overall_thesis_score": 0.5, "core_grid_wins": 3, "checkpoint_fallback_actions": 0},
        {"run_number": 2, "overall_thesis_score": 0.5, "core_grid_wins": 4, "checkpoint_fallback_actions": 0},
        {"run_number": 3, "overall_thesis_score": 0.5, "core_grid_wins": 4, "checkpoint_fallback_actions": 1},
    ]
)
assert selected["run_number"] == 2
```

Test that pooled metrics contain rows from every attempted run and that
`exploratory_selected_run` is true when attempt count exceeds one.

- [ ] **Step 2: Run and verify RED**

Expected: missing search helpers.

- [ ] **Step 3: Implement deterministic search configurations**

For run number `n`:

```python
run_seed_start = seed_start + (n - 1) * seed_count
run_stress_profile = profiles[(n - 1) % len(profiles)]
```

Use profiles `standard`, `grid_heavy`, and `constrained`. Each profile changes
only documented request transformation intensity and area strategy.

Export each attempt to:

```text
search_runs/search_run_<n>/summary_metrics.json
search_runs/search_run_<n>/feeder_eval_results.csv
search_runs/search_run_<n>/scenario_config.json
```

- [ ] **Step 4: Implement selection and pooled evidence**

Sort by:

```python
(
    overall_thesis_score,
    core_grid_wins,
    -checkpoint_fallback_actions,
    -run_number,
)
```

descending. Stop searching when the target is met or max runs is reached.
Write:

- `search_summary.csv`
- `search_summary.json`
- `selected_run_reason.txt`
- pooled policy metrics inside top-level `summary_metrics.json`.

The reason file must state the composite, tie-break, target status, and whether
selection is exploratory.

- [ ] **Step 5: Run focused tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: add transparent feeder evaluation search"
```

## Phase E: Reports, Figures, And Secondary Cost Context

### Task 8: Generate All Required Feeder Figures

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing figure contract test**

With `pytest.importorskip("matplotlib")`, export synthetic evidence and assert:

```python
required = [
    "summary_table.png",
    "grid_safety_improvement_vs_random.png",
    "violation_counts_by_policy.png",
    "opf_infeasible_by_policy.png",
    "mean_stress_by_policy.png",
    "curtailment_by_policy.png",
    "feasible_energy_by_policy.png",
    "reward_by_policy.png",
    "duration_by_policy.png",
    "distance_by_policy.png",
    "service_quality_by_policy.png",
    "invalid_and_fallback_actions.png",
    "served_vs_missed_requests.png",
    "per_seed_reward_distribution.png",
    "checkpoint_vs_random_per_seed.png",
    "checkpoint_vs_weighted_per_seed.png",
]
for name in required:
    assert (tmp_path / "figures" / name).is_file()
```

Assert cost figures are absent when cost is unavailable and present when
`cost_service_summary["available"]` is true:

```python
assert not (tmp_path / "figures" / "user_cost_by_policy.png").exists()
assert not (tmp_path / "figures" / "cost_grid_tradeoff.png").exists()
```

For the available-cost fixture:

```python
assert (tmp_path / "figures" / "user_cost_by_policy.png").is_file()
assert (tmp_path / "figures" / "cost_grid_tradeoff.png").is_file()
```

- [ ] **Step 2: Run and verify RED**

Expected: missing plot functions.

- [ ] **Step 3: Implement Matplotlib-only plots**

Use:

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
```

Every helper creates one `fig, ax`, saves one PNG, and closes it. Do not use
subplots or seaborn.

For unavailable feeder distance/duration, generate a labeled figure containing:

```text
Metric unavailable in primary feeder evaluator.
See secondary_app_cost_evidence when enabled.
```

Do not substitute app values into feeder plots.

- [ ] **Step 4: Run focused tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: render feeder thesis figures"
```

### Task 9: Generate Honest Report And Nonblank Claims

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing report wording tests**

Assert the report includes:

- `Executive Summary`
- `Benchmark Configuration`
- `Main Results`
- `Grid Safety Improvement`
- `User Cost And Service Context`
- `Statistical Summary`
- `Figures`
- `Thesis-Safe Wording`
- `Limitations`
- `weighted` and `oracle-like greedy grid-aware heuristic`
- feeder evidence is primary;
- app evidence is secondary;
- app success rate is excluded.

For an unmet target, assert the exact sentence:

```text
The tested checkpoint did not demonstrate the target advantage under the evaluated stress scenarios.
```

- [ ] **Step 2: Run and verify RED**

- [ ] **Step 3: Implement report and claim renderers**

Strong claims require target met. Balanced claims require at least one core
grid win but target unmet. Negative claims cover zero wins or broad
underperformance.

Cost wording is emitted only when `cost_service_summary.available` is true and
must begin with:

```text
Secondary user-cost context:
```

Never state that the feeder checkpoint directly optimized cost unless direct
feeder price metadata exists.

- [ ] **Step 4: Run focused tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: generate thesis-safe feeder reports"
```

### Task 10: Add Secondary App Cost Evidence On The Same Generated Requests

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing evidence-separation test**

Use fake app responses and assert:

- output directory is `secondary_app_cost_evidence`;
- policies are exactly `weighted_score`, `cheapest`, `fastest`, `closest`,
  `rl_maskable_ppo_feeder`;
- summary includes cost, duration, distance, wait, and fallback diagnostics;
- summary does not expose app success rate as a feeder metric;
- primary composite is unchanged.

- [ ] **Step 2: Implement feeder-to-app request adapter**

Convert the selected run's unique `FeederRequest` objects into valid
`ExternalChargingRequest` objects. Preserve request energy, SoC, deadline,
coordinates when available, and feeder area in metadata:

```python
metadata={
    "secondary_area_id": request.secondary_area_id,
    "evidence_scope": "secondary_app_cost_evidence",
    "source_feeder_request_id": request.request_id,
}
```

Use the same selected request set for every app policy.

- [ ] **Step 3: Implement side-effect-contained app evaluation**

Inside `run_secondary_app_cost_evidence`, lazily import app/runtime classes,
start one Dundee replay environment, build candidate contexts, and run the five
policies. Write:

```text
secondary_app_cost_evidence/app_cost_results.csv
secondary_app_cost_evidence/app_cost_results.json
secondary_app_cost_evidence/cost_service_summary.json
secondary_app_cost_evidence/run_metadata.json
```

Record failures and available-row counts honestly. Do not silently drop failed
policy/request rows.

- [ ] **Step 4: Add cost claims and figures conditionally**

Generate cost claims only when comparable rows exist for checkpoint and the
named baseline. Valid patterns:

```text
RL reduced grid risk at an average estimated cost premium of £X compared with cheapest.
```

or:

```text
RL reduced average estimated cost compared with fastest/closest while the primary feeder evaluation showed lower grid risk than random.
```

- [ ] **Step 5: Run focused tests and commit**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: add secondary app cost context"
```

## Phase F: CLI, Strict Validation, Documentation, And Verification

### Task 11: Complete CLI And Strict End-To-End Behavior

**Files:**
- Modify: `tests/verification/test_feeder_rl_thesis_evaluation.py`
- Modify: `scripts/verification/export_feeder_rl_thesis_evaluation.py`

- [ ] **Step 1: Write failing CLI tests**

Test `parse_args([...])` for every required flag:

```text
--mode
--seed-start
--seed-count
--duration-hours
--scenario-count
--output-dir
--checkpoint-path
--feeder-rl-data-dir
--policies
--stress-profile
--require-replay-covered-area
--strict
--keep-searching
--max-search-runs
--target-rl-advantage
```

Also add:

```text
--include-secondary-app-cost-evidence
```

Assert unsupported policies and nonpositive counts fail argument parsing.
Implement `--require-replay-covered-area` with
`argparse.BooleanOptionalAction` and `default=True`, so the required replay
coverage is the normal behavior while diagnostic runs can explicitly use
`--no-require-replay-covered-area`.

- [ ] **Step 2: Implement config and main orchestration**

Add `EvaluationConfig` and make `main(argv: Sequence[str] | None = None) -> int`.
Order:

1. parse and validate config;
2. validate artifacts and replay provenance;
3. load repository and checkpoint once;
4. run one evaluation or transparent search;
5. run optional selected-request app cost evidence;
6. export selected and pooled evidence;
7. validate outputs;
8. print concise result paths and target status;
9. return nonzero only for operational/strict contract failures, not for an
   honestly unmet scientific target.

- [ ] **Step 3: Add strict checks**

Strict checks include:

- artifact presence;
- replay row count and covered area count;
- truth levels at least `area_pf`;
- zero adapter-proxy rows;
- checkpoint observation shape equals environment shape;
- exact policy/request fingerprint parity;
- mode seed/request minimums;
- checkpoint inference attempted;
- zero checkpoint fallback and invalid actions;
- complete output files and figures;
- one nonblank claim category.

- [ ] **Step 4: Run focused tests**

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests\verification\test_feeder_rl_thesis_evaluation.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit CLI**

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py
git commit -m "feat: complete feeder thesis evaluation CLI"
```

### Task 12: Document PR 6.1 Evidence Boundaries

**Files:**
- Modify: `docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md`
- Modify: `scripts/verification/README.md`

- [ ] **Step 1: Add primary vs secondary documentation**

Document:

- old app benchmark is runtime smoke evidence;
- new feeder exporter is primary performance evidence;
- exact commands for quick/thesis/stress;
- output inventory;
- search selection and pooled evidence;
- weighted oracle-like comparator;
- cost claims are secondary unless feeder price metadata exists;
- offline `area_pf` / `area_reuse`, not closed-loop or MARL.

- [ ] **Step 2: Check documentation references**

Run:

```powershell
rg -n "export_feeder_rl_thesis_evaluation|thesis_feeder_rl_evaluation|secondary_app_cost_evidence" docs scripts/verification
```

Expected: references appear in the runbook, README, script, and focused tests.

- [ ] **Step 3: Commit documentation**

```powershell
git add docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md scripts/verification/README.md
git commit -m "docs: add feeder RL thesis evaluation runbook"
```

### Task 13: Run Verification Matrix And Inspect Real Evidence

**Files:**
- No code changes unless a failing verification is reproduced with a test first.

- [ ] **Step 1: Run focused tests**

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests\verification\test_feeder_rl_thesis_evaluation.py -q
```

- [ ] **Step 2: Run quick benchmark with transparent search**

```powershell
uv run --with pyarrow --with pydantic --with numpy --with pandas --with matplotlib --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\export_feeder_rl_thesis_evaluation.py --mode quick --strict --keep-searching --max-search-runs 5 --include-secondary-app-cost-evidence
```

Inspect:

- request count at least 150;
- every search run exported;
- selected reason documented;
- pooled metrics present;
- claim category nonblank;
- zero checkpoint invalid/fallback actions;
- actual target status, without assuming pass.

- [ ] **Step 3: Run full tests**

```powershell
uv run --with pytest --with pydantic --with numpy --with pandas pytest tests -q
```

- [ ] **Step 4: Run PR 4 no-fallback verifier**

```powershell
uv run --with pyarrow --with pydantic --with numpy --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\verify_feeder_rl_api_no_fallback.py --strict
```

- [ ] **Step 5: Run PR 5 forecast verifier**

```powershell
uv run --with pydantic --with numpy --with pandas --with joblib --with tensorflow --with scikit-learn python scripts\verification\verify_forecasting_provider.py --provider keras_load_kw_30min --model-dir models\forecasting\load_kw_30min --strict --allow-smoke-template
```

- [ ] **Step 6: Run thesis benchmark**

```powershell
uv run --with pyarrow --with pydantic --with numpy --with pandas --with matplotlib --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\export_feeder_rl_thesis_evaluation.py --mode thesis --strict --keep-searching --max-search-runs 10 --target-rl-advantage --include-secondary-app-cost-evidence
```

Inspect at least 750 unique requests and record all real headline metrics.

- [ ] **Step 7: Run stress benchmark if runtime permits**

```powershell
uv run --with pyarrow --with pydantic --with numpy --with pandas --with matplotlib --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\export_feeder_rl_thesis_evaluation.py --mode stress --strict --keep-searching --max-search-runs 10 --target-rl-advantage
```

If not run due to time or compute, state that explicitly in the final response.

- [ ] **Step 8: Review final diff and evidence honesty**

Run:

```powershell
git diff --check
git status --short
```

Verify no checkpoint, observation, reward, app schema, forecast-to-RL, live
DigitalTwin, or MARL files changed.

- [ ] **Step 9: Final implementation commit**

Stage only PR 6.1 files and any test-first fixes produced during verification:

```powershell
git add scripts/verification/export_feeder_rl_thesis_evaluation.py tests/verification/test_feeder_rl_thesis_evaluation.py docs/ev_side/THESIS_BENCHMARK_EVIDENCE_RUNBOOK.md scripts/verification/README.md
git commit -m "feat: export thesis-grade feeder RL evaluation"
```

## Completion Evidence

The final response must report actual values from the selected and pooled
outputs:

- files changed;
- why the original app success benchmark was insufficient;
- search attempts and selection reason;
- policies, seeds, scenarios, and unique request count;
- six core checkpoint-vs-random metrics;
- checkpoint-vs-weighted result;
- invalid/fallback rates;
- direct feeder cost availability;
- secondary app cost comparisons when available;
- report, claims, figure, and output paths;
- every verification command and result;
- whether thesis/stress modes were actually run;
- offline replay and `area_pf` / `area_reuse` limitations.
