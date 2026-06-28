# RL Safety Filter With Preference Ranking Design

## Purpose

PR 6.2 changes the app recommendation architecture from two separate choices
(deterministic preference ranking or feeder RL ranking) into an explicit hybrid:

```text
feeder RL/grid advisory safety layer
-> deterministic user preference ranker
-> unchanged RecommendationResponse schema
```

The final app order remains governed by `closest`, `cheapest`, `fastest`, or
`weighted_score`. Feeder RL contributes bounded safety penalties, optional
blocking, and diagnostics. It does not become the final preference ranker.

PR 6.1 implementation remains paused. Its committed design and plan are retained
as feeder-evaluator evidence infrastructure. Hybrid thesis benchmarking is
future PR 6.3 scope.

## Non-Negotiable Boundaries

PR 6.2 does not:

- change `ExternalChargingRequest`, `RecommendationOption`, or
  `RecommendationResponse`;
- change the trained feeder checkpoint;
- change the 2200-feature feeder observation;
- change feeder reward logic;
- inject forecast features into RL;
- implement live DigitalTwin closed-loop control;
- implement MARL;
- fabricate a physical Dundee-to-feeder station mapping;
- use app success rate as feeder grid-performance evidence.

Default deterministic behavior and API startup remain free of Torch,
Stable-Baselines3, and sb3-contrib requirements.

## Hybrid Policies

Register:

- `rl_safety_closest`
- `rl_safety_cheapest`
- `rl_safety_fastest`
- `rl_safety_weighted`
- `rl_safety_preference`

Each explicit hybrid policy wraps the existing deterministic policy:

| Hybrid policy | Wrapped final ranker |
|---|---|
| `rl_safety_closest` | `ClosestPolicy` |
| `rl_safety_cheapest` | `CheapestPolicy` |
| `rl_safety_fastest` | `FastestPolicy` |
| `rl_safety_weighted` | `WeightedScorePolicy` |

`rl_safety_preference` chooses the wrapped policy from the original request
`preference_mode`. Supported preference modes map as:

- `closest` -> `ClosestPolicy`
- `cheapest` -> `CheapestPolicy`
- `fastest` -> `FastestPolicy`

If a non-app internal request supplies `weighted_score`, the generic policy may
select `WeightedScorePolicy`. Unknown values fail clearly or use the repository's
existing deterministic fallback convention; they must not silently become raw
feeder RL ranking.

## Component Boundary

Create:

```text
packages/ev_core/src/ev_core/recommender/rl_safety_filter.py
```

The module contains:

- an immutable safety configuration;
- candidate-to-feeder mapping helpers;
- advisory-to-safety scoring;
- a result/diagnostic contract;
- a hybrid policy wrapper that composes an existing deterministic policy with
  the safety filter.

The public operation is equivalent to:

```python
apply_rl_safety_filter(
    request,
    base_options,
    runtime_context,
    preference_mode,
    config,
) -> SafetyFilterResult
```

The filter accepts options that have already been scored by the selected
deterministic ranker. This makes the existing policy implementation the single
source of truth for distance, dynamic cost, duration/wait, and weighted scores.

## Data Flow

1. `DundeeEnv` builds ordinary app `CandidateContext` objects, including
   dynamic price, estimated cost, distance, duration, wait, queue, utilization,
   transformer headroom, and compatibility.
2. A hybrid policy is selected.
3. `DundeeEnv` builds the existing feeder runtime context:
   - `feeder_observation`
   - `feeder_action_mask`
   - `feeder_station_ids`
   - `grid_advisories`
4. The wrapped deterministic policy ranks all app candidates and produces
   `base_preference_score`.
5. The safety layer lazily runs feeder checkpoint inference when enabled and
   maps app options to feeder actions according to the configured mapping mode.
6. The safety layer derives candidate safety score, penalty, status, reason,
   and mapping provenance.
7. Penalty mode adjusts only the normalized option score. Block mode may remove
   unsafe options.
8. `RecommendationService` assembles the unchanged response and merges hybrid
   diagnostics into existing metadata dictionaries.

## Configuration

Extend `RecommendationConfig` with:

- `rl_safety_filter_enabled: bool = False`
- `rl_safety_filter_mode: str = "penalty"`
- `rl_safety_filter_strict: bool = False`
- `rl_safety_filter_penalty_weight: float = 0.25`
- `rl_safety_block_unsafe: bool = False`
- `rl_safety_mapping_mode: str = "exact_only"`

Environment variables:

- `RL_SAFETY_FILTER_ENABLED`
- `RL_SAFETY_FILTER_MODE`
- `RL_SAFETY_FILTER_STRICT`
- `RL_SAFETY_FILTER_PENALTY_WEIGHT`
- `RL_SAFETY_BLOCK_UNSAFE`
- `RL_SAFETY_MAPPING_MODE`

Supported values:

- safety mode: `penalty`, `block`
- mapping mode: `exact_only`, `stable_ordinal_demo_bridge`

Penalty weight is validated and bounded to `[0.0, 1.0]`. Invalid enum or
numeric values fail clearly using the existing config-validation style.

Selecting an `rl_safety_*` policy explicitly enables the hybrid operation for
that request even when the global enable flag is false. The flag controls
automatic/optional hybrid activation and remains `false` by default.

`RL_SAFETY_FILTER_STRICT` governs hybrid context, inference, and mapping
failure. `RL_POLICY_FAIL_CLOSED` remains honored for checkpoint inference.
Fail-closed behavior is active if either applicable strict/fail-closed setting
requires it.

## Deterministic Base Ranking

The wrapped policy runs before safety adjustment.

- `ClosestPolicy` computes its existing normalized score from distance.
- `CheapestPolicy` computes its existing normalized score from
  `estimated_cost_gbp`, which already contains dynamic pricing.
- `FastestPolicy` computes its existing normalized score from duration plus
  wait.
- `WeightedScorePolicy` computes its existing weighted heuristic score.

The resulting option score is copied to:

```text
base_preference_score
```

The safety layer must not reimplement or approximate these formulas.

## Penalty Mode

Penalty mode retains every option and uses:

```text
adjusted_score =
    base_preference_score
    - penalty_weight * safety_penalty
```

Where:

- `base_preference_score` is the score produced by the wrapped deterministic
  ranker;
- `safety_penalty` is bounded to `[0.0, 1.0]`;
- `penalty_weight` is bounded to `[0.0, 1.0]`;
- higher adjusted score remains better.

Sorting uses adjusted score descending with a stable sort over the wrapped
policy's already-ranked output. Equal adjusted scores therefore preserve the
existing deterministic ranker's original order and tie-break behavior without
duplicating its internals.

Penalty mode changes only:

- option `score`;
- safety metadata;
- safety reason tags where useful.

It does not mutate:

- `distance_km`
- `estimated_cost_gbp`
- `estimated_duration_minutes`
- `estimated_wait_minutes`
- `price_per_kwh`
- dynamic pricing metadata
- `current_queue`
- `utilization`
- `transformer_headroom_kw`
- connector compatibility or station identity.

Two identity guarantees are required:

- `penalty_weight=0.0` produces the original deterministic ordering;
- all `safety_penalty=0.0` produces the original deterministic ordering.

## Block Mode

Candidates marked unsafe/blocked are removed only when:

- safety mode is `block`, or
- `RL_SAFETY_BLOCK_UNSAFE=true`.

If at least one candidate remains, the wrapped deterministic order is
preserved among remaining candidates, with bounded score adjustment only if
the selected mode also applies a penalty.

If all candidates are blocked:

- fail-open restores the original deterministic options unchanged in order,
  adds filter-fallback diagnostics, and records why blocking was not enforced;
- fail-closed returns an empty list, allowing existing service conventions to
  produce controlled no-option behavior.

No hidden deterministic result may be returned in fail-closed mode.

## Candidate-To-Feeder Mapping

### Exact Mapping

Mapping precedence starts with:

1. exact station ID equality; then
2. an explicit documented mapping table supplied through runtime context or a
   future verified artifact.

Exact mapping metadata:

```text
rl_safety_mapping_kind=exact
rl_safety_mapping_physical_claim=true
rl_mapped_feeder_station_id=<id>
rl_mapped_feeder_action_index=<index>
```

`physical_claim=true` is used only for an identity that is actually documented
or exactly shared by both catalogs.

### Exact-Only Unmapped

With `RL_SAFETY_MAPPING_MODE=exact_only`, unmatched app candidates receive:

```text
rl_safety_status=unmapped
rl_safety_penalty=0.0
rl_safety_mapping_kind=unmapped
rl_safety_mapping_physical_claim=false
rl_safety_reason=no_candidate_feeder_mapping
```

Candidate-level safety adjustment is not fabricated. If every candidate is
unmapped, the filter reports `rl_safety_filter_applied=false` and preserves the
deterministic ranking.

### Stable Ordinal Demo Bridge

With `stable_ordinal_demo_bridge`, unmatched candidates map deterministically:

1. Sort app candidate station IDs lexicographically.
2. Sort valid feeder `(station_id, action_index)` pairs lexicographically by
   station ID and then action index.
3. Assign the candidate at ordinal `i` to valid feeder ordinal
   `i % valid_feeder_action_count`.

The mapping depends only on stable ordered identifiers and the current valid
feeder action catalog. Python's salted `hash()` is prohibited. SHA-256 may be
used for stable tie-breaking if duplicate identifiers require it.

Bridge metadata:

```text
rl_safety_mapping_kind=stable_ordinal_demo_bridge
rl_safety_mapping_physical_claim=false
offline_feeder_rl_adapter=true
rl_safety_mapping_warning=nonphysical_demo_mapping
rl_mapped_feeder_station_id=<id>
rl_mapped_feeder_action_index=<index>
```

The bridge demonstrates app architecture only. It does not establish physical
Dundee-to-feeder identity and cannot support primary grid-performance claims.

## Checkpoint Inference

The safety layer reuses the established feeder checkpoint validation:

- lazy model loading;
- expected observation size;
- action-mask/station-ID length;
- at least one valid action;
- deterministic masked prediction;
- predicted action range and mask validation.

Inference produces:

- `rl_selected_feeder_station_id`
- `rl_selected_action_index`
- `fallback_used`
- inference diagnostics.

The selected feeder action may receive a lower penalty or a `preferred_safe`
reason when its recorded advisory supports that status. The selected action is
advisory context only and must not be moved directly to the top of the app
ranking.

## Safety Scoring

For a mapped feeder advisory, compute an explainable bounded risk value from:

- recorded stress score;
- voltage violation count;
- line overload count;
- transformer overload count;
- OPF feasibility;
- curtailment required.

Each normalized component is bounded to `[0.0, 1.0]`. The candidate risk is a
documented weighted average, initially:

```text
risk =
    0.30 * stress_risk
    + 0.15 * voltage_risk
    + 0.15 * line_risk
    + 0.15 * transformer_risk
    + 0.15 * opf_risk
    + 0.10 * curtailment_risk
```

Normalization:

- `stress_risk = clamp(stress_score, 0, 1)`
- violation/overload risks are `1` when count is positive, otherwise `0`
- `opf_risk = 1` when infeasible, otherwise `0`
- `curtailment_risk = clamp(curtailment_required_kw / 22.0, 0, 1)`

Then:

```text
safety_penalty = clamp(risk, 0, 1)
safety_score = 1 - safety_penalty
```

The 22 kW curtailment scale matches the installed action catalog's current
charger power and must be exposed as a named constant, not buried in code.

Suggested statuses:

- `safe`: penalty `< 0.25`
- `caution`: penalty `< 0.60`
- `risky`: penalty `>= 0.60`
- `blocked`: configured blocking applies to a risky/reject candidate
- `unmapped`: exact-only candidate has no mapping
- `unavailable`: context, advisory, or inference is unavailable.

An explicit `REJECT`, `VIOLATION`, or infeasible OPF advisory is block-eligible.
The checkpoint-selected action does not override these recorded safety facts.

## Candidate Metadata

Every hybrid option includes:

- `base_preference_score`
- `rl_safety_filter_enabled`
- `rl_safety_filter_mode`
- `rl_safety_status`
- `rl_safety_score`
- `rl_safety_penalty`
- `rl_safety_penalty_weight`
- `rl_safety_adjusted_score`
- `rl_safety_blocked`
- `rl_safety_reason`
- `rl_safety_mapping_kind`
- `rl_safety_mapping_physical_claim`
- `rl_safety_mapping_warning`, when applicable
- `rl_mapped_feeder_station_id`, when mapped
- `rl_mapped_feeder_action_index`, when mapped
- `rl_selected_feeder_station_id`, when inference succeeds
- `rl_selected_action_index`, when inference succeeds
- `feeder_selected_secondary_area_id`
- `feeder_area_strategy`
- `feeder_valid_action_count`
- `grid_truth_level`
- `grid_label_source_kind`
- `offline_feeder_rl_adapter`
- `fallback_used`.

Metadata uses existing dictionaries only.

## Response Metadata

`RecommendationService` merges hybrid diagnostics into response metadata:

- `effective_policy_name`
- `requested_policy_name`
- `policy_source`
- `preference_mode`
- `final_ranker`
- `rl_safety_filter_enabled`
- `rl_safety_filter_applied`
- `rl_safety_filter_mode`
- `rl_safety_mapping_mode`
- `rl_safety_candidates_penalized`
- `rl_safety_candidates_blocked`
- `rl_safety_filter_fallback_used`
- `rl_safety_filter_reason`
- `fallback_used`
- `dynamic_pricing_enabled`, when present in option metadata
- existing forecast metadata, unchanged.

The service should derive these diagnostics from a stable hybrid result or
option metadata without adding response fields.

## Runtime Integration

`DundeeEnv.get_ranked_recommendations(...)` builds feeder runtime context when:

- the selected policy name is `rl_maskable_ppo_feeder`;
- the selected policy is any `rl_safety_*` policy; or
- automatic safety filtering is explicitly enabled.

It preserves the original request `preference_mode`.

The policy registry creates hybrid policies without eagerly importing or
loading ML dependencies. Model import occurs only during enabled hybrid
inference.

Policy selection precedence remains:

```text
FORCE_RECOMMENDATION_POLICY
-> RECOMMENDATION_POLICY_NAME
-> explicit service policy
-> request preference
-> weighted_score default
```

No environment setting silently replaces the user's stored preference value.

## Failure Behavior

### Fail Open

If feeder context, optional dependencies, checkpoint, mapping, advisory, or
prediction is unavailable:

- preserve deterministic preference ranking;
- leave raw option fields unchanged;
- set adjusted score equal to base score;
- set `rl_safety_filter_applied=false` when no meaningful penalty was applied;
- expose the exact failure reason;
- set filter fallback metadata.

### Fail Closed

If strict/fail-closed behavior is active:

- return no options for required context/inference failures;
- return no options when block mode removes all candidates;
- do not silently return deterministic recommendations;
- preserve controlled service/API response behavior.

## Dynamic Pricing And Forecasting

Dynamic pricing remains calculated in the app candidate layer before ranking.
`CheapestPolicy` continues to use dynamic `estimated_cost_gbp`, and
`WeightedScorePolicy` continues to use its existing cost component.

The safety layer does not edit:

- final price per kWh;
- estimated cost;
- tariff metadata;
- pricing multipliers.

Forecast metadata remains diagnostic/smoke only. It is merged as before and is
not added to the 2200-feature feeder observation or safety score.

## Verifier

Create:

```text
scripts/verification/verify_rl_safety_preference_ranking.py
```

It compares baseline and hybrid behavior for:

- closest;
- cheapest;
- fastest;
- weighted score.

It verifies:

- response schemas are unchanged;
- the final ranker name is preserved;
- baseline behavior is unchanged when safety is disabled;
- safety metadata appears only in enabled hybrid paths;
- checkpoint fallback is false in strict artifact-complete mode;
- dynamic pricing fields remain present;
- raw option fields remain unchanged by penalty application;
- zero penalty weight preserves baseline order;
- zero candidate penalties preserve baseline order;
- a sufficiently risky candidate moves down;
- exact-only unmatched candidates remain unpenalized;
- ordinal bridge mapping is stable and explicitly nonphysical;
- controlled block and all-blocked behavior.

## Tests

Add focused tests for:

- config defaults and validation without ML dependencies;
- hybrid policy registration;
- explicit/generic wrapped ranker selection;
- closest, cheapest, fastest, and weighted base ranking preservation;
- penalty equation and bounds;
- zero-weight identity;
- zero-penalty identity;
- risky-candidate demotion;
- raw option-field immutability;
- dynamic cost as cheapest base score;
- candidate base/adjusted score metadata;
- exact mapping;
- exact-only unmapped behavior;
- deterministic stable ordinal bridge;
- nonphysical bridge metadata;
- penalty mode retention;
- block mode removal;
- all-blocked fail-open restoration;
- all-blocked fail-closed empty result;
- missing dependency/context fail-open;
- missing dependency/context fail-closed;
- response-level diagnostics;
- unchanged response schema;
- default deterministic startup without Torch/SB3.

## Documentation

Update the requested architecture, readiness, runtime-artifact, runbook, plan,
and environment-example documents. They must state:

- deterministic preference ranking remains the default;
- hybrid mode uses feeder RL as safety/advisory context;
- final ranking remains user-preference based;
- dynamic pricing still drives cheapest/weighted cost terms;
- feeder RL is not preference-conditioned;
- the checkpoint remains 2200 features;
- forecast metadata is not fed into RL;
- ordinal mapping is nonphysical app/demo evidence only;
- primary grid-performance evidence remains feeder-evaluator evidence;
- live DigitalTwin and MARL remain future work.

## Acceptance

PR 6.2 is complete when:

- all five hybrid policies are registered;
- default deterministic policies are behaviorally unchanged;
- penalty and block modes meet this specification;
- candidate and response diagnostics are present;
- exact-only and stable bridge mapping behave as specified;
- dynamic pricing and forecast behavior remain intact;
- optional ML dependencies remain optional when hybrid safety is disabled;
- hybrid verifier passes;
- PR 4 no-fallback verifier passes;
- PR 5 forecast verifier passes;
- focused and full test suites pass;
- no schema, checkpoint, observation, live-control, MARL, or PR 6.1
  implementation changes are introduced.
