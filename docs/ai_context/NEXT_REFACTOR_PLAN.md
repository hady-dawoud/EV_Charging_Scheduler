# Next Refactor Plan

Do not implement this until the next implementation prompt. Preserve the current mobile/API/dashboard response shape.

## Goal

Make recommendation ranking explicit, testable, and replaceable without changing current API behavior. Baselines should become first-class. MARL checkpoint inference should wait until the policy interface, baseline tests, and request validation are stable.

## Recommended Next PR

Create a thin policy abstraction around the current weighted heuristic ranker and add focused tests for existing behavior.

## Constraints

- Keep FastAPI thin.
- Preserve `ExternalChargingRequest`, `RecommendationOption`, and `RecommendationResponse` field names.
- Preserve mobile result mapping in `apps/mobile/src/screens/ResultsScreen.tsx`.
- Preserve dashboard reads until there is a deliberate API/dashboard migration PR.
- Do not extract candidate building in the first PR unless tests require a tiny adapter.
- Do not add MARL inference in the first PR.

## Proposed Shape

Introduce a policy interface conceptually equivalent to:

```python
policy.rank(request, candidates, runtime_context)
```

Where:

- `request` is the internal request or a small request view.
- `candidates` are candidate contexts.
- `runtime_context` contains simulated timestamp, forecasts, policy mode, or other runtime metadata needed later.

The first implementation should wrap the current `WeightedHeuristicRanker` as `WeightedScorePolicy`, not replace behavior.

## Step Plan

1. Add characterization tests around current `WeightedHeuristicRanker`.
   - Verify preference-mode weights affect ordering.
   - Verify deterministic tie-break sorting.
   - Verify reason tag thresholds.
   - Verify unknown preference mode defaults to `fastest`.

2. Add tests for `RecommendationService.recommend`.
   - Top recommendation is ranked item 0.
   - Alternatives are ranked items 1 through 3.
   - No candidates returns `top_recommendation=None` and no feasible station note.
   - Response shape remains unchanged.

3. Add a policy abstraction without changing public response models.
   - Candidate name: `RecommendationPolicy` or `RankingPolicy`.
   - Method: `rank(request, candidates, runtime_context)`.
   - Keep adapter compatibility with `CandidateRanker.rank(RecommendationInput)` if needed.

4. Wrap current ranker.
   - `WeightedScorePolicy` should delegate to the existing score formula.
   - Outputs should remain `RecommendationOption` with identical fields.
   - The existing `WeightedHeuristicRanker` can remain temporarily as the scoring implementation to reduce risk.

5. Make baseline policies first-class for recommendation ranking.
   - Keep existing allocation policies in `env/baselines.py` for simulation allocation.
   - Add explicit recommendation baselines only after clarifying whether they rank candidates or choose one option.
   - Suggested baselines: closest-only, cheapest-only, fastest-service, overload-aware weighted score.

6. Extract candidate building later.
   - Current candidate construction is coupled to `DundeeEnv._build_candidate_contexts`.
   - Extract only after policy interface tests pass.
   - Target shape: candidate builder returns candidate contexts from station/runtime/forecast state without owning ranking logic.

7. Strengthen request validation later.
   - Add domain validation to `ExternalChargingRequest` after capturing current accepted payloads in tests.
   - Validate SOC ranges, battery capacity, positive energy, latest finish after request timestamp, coordinate bounds, and mismatch behavior.

8. Add MARL checkpoint inference last.
   - Do not introduce RL/MARL dependencies until baseline policies, candidate building, and runtime-context contracts are stable.
   - Decide checkpoint framework and observation/action schema first.

## Acceptance Criteria For The Next PR

- Existing mobile `POST /recommendations` still works with the same JSON field names.
- Dashboard recommendation panel still reads stored `RecommendationResponse` objects.
- Tests prove current weighted heuristic behavior before and after the abstraction.
- No MARL/RL dependency is added.
- API endpoint remains a thin call into runtime service.

