# Feeder RL Thesis Evaluation Design

## Purpose

PR 6.1 adds a standalone, replay-backed thesis evaluation exporter for the
trained feeder MaskablePPO checkpoint. The primary evidence compares `random`,
`weighted`, and `checkpoint` policies inside the feeder station-selection
environment. It evaluates grid safety, reward, service, masking, and replay
provenance rather than treating app recommendation success as policy
performance.

The exporter must not modify the production checkpoint, the 2200-feature
observation contract, the feeder reward model, app/API/mobile schemas, or
forecast integration. The work remains offline, single-agent, and replay
backed.

## Primary Entry Point

Create:

```text
scripts/verification/export_feeder_rl_thesis_evaluation.py
```

Default output:

```text
outputs/thesis_feeder_rl_evaluation/<timestamp>/
```

The exporter directly uses the feeder repository, scenario/request contracts,
`FeederStationSelectionEnv`, recorded grid advisories, and the final
MaskablePPO checkpoint. It does not import the existing app benchmark exporter
for primary feeder evaluation.

## Evaluation Architecture

The exporter has five internal responsibilities:

1. Build deterministic stress scenario definitions and request sets.
2. Evaluate the same request set with every selected feeder policy.
3. Aggregate per-request results into seed, scenario, policy, and run metrics.
4. Run an optional transparent search over deterministic seed windows and
   stress tiers.
5. Export machine-readable evidence, reports, thesis-safe claims, and separate
   Matplotlib figures.

These responsibilities may remain in one executable script if the resulting
helpers are focused and independently testable. No production package
abstraction is required unless implementation reveals reusable feeder
evaluation behavior that cannot be tested cleanly from the script.

## Fair Request Replay

For each seed and scenario, generate one deterministic list of
`FeederRequest` objects before any policy is evaluated. Every policy receives a
fresh environment reset backed by an immutable copy of that exact request
list.

A benchmark-only request generator adapter may return the pre-generated
requests from `generate_for_scenario`. This preserves normal environment
observation, action-mask, grid-advisory, and reward behavior while preventing
policy-specific request resampling.

Policy randomness is deterministic and isolated. Random-policy action choices
use a seed derived from the benchmark run, scenario, and seed. Weighted and
checkpoint policies are deterministic for the same observation and mask.

## Scenario Matrix

The required scenarios are:

- `normal_replay`
- `evening_peak`
- `high_demand`
- `deadline_pressure`
- `low_soc_urgent`
- `constrained_replay_area`
- `grid_stress_heavy`
- `mixed_service_cost`

Each scenario starts from valid feeder requests and applies deterministic,
benchmark-only transformations:

- arrival-hour concentration for evening demand;
- requested-energy, battery, and SoC adjustments for high demand;
- shorter latest-finish windows for deadline pressure;
- low SoC plus high energy for urgent service;
- selection of replay-covered areas with fewer valid actions;
- preference for replay-covered areas with worse recorded stress indicators;
- balanced requests for service and cost context.

Transformations must preserve valid request contracts and use only information
available in installed artifacts. They must not alter environment reward logic,
checkpoint observations, model parameters, or replay labels.

## Modes And Counts

Mode defaults must satisfy:

| Mode | Minimum seeds | Minimum evaluated requests |
|---|---:|---:|
| `quick` | 10 | 150 |
| `thesis` | 50 | 750 |
| `stress` | 90 | 1500 |

`--seed-count`, `--scenario-count`, and duration/request controls may increase
or explicitly override defaults, but strict mode must reject a completed run
that falls below the selected mode's minimum request count.

An evaluated request means one unique feeder request. Policy rows are reported
separately and do not multiply the headline request count.

## Feeder Policies

The primary comparison contains:

- `random`: choose uniformly from the current valid action mask;
- `weighted`: choose the valid action with the highest existing feeder reward;
- `checkpoint`: call the final MaskablePPO checkpoint with the unmodified
  observation and action mask.

The default checkpoint is:

```text
models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip
```

Checkpoint predictions outside the valid mask are counted as fallback actions.
The valid fallback action is recorded so evaluation can continue, but strict
mode fails after exporting diagnostics if checkpoint fallback or invalid
actions occur.

The weighted policy is a strong greedy grid-aware comparator with direct access
to the existing reward calculation for every valid action. It can therefore be
described as oracle-like relative to a learned one-step policy. The primary
scientific target is checkpoint improvement over random/grid-unaware selection.
Checkpoint comparison with weighted is reported honestly and is not forced to
pass.

## Replay Boundary

Primary evaluation uses:

- `grid_advisory_mode=recorded`
- `grid_evaluation_mode=replay`
- `min_truth_level=area_pf`
- `exclude_adapter_proxy=true`
- replay-covered feeder areas only when required

Run metadata records actual action count, replay row count, replay-covered area
count, truth-level counts, and label-source counts. The report identifies
`area_pf` / `area_reuse` as the installed evidence boundary.

## Request-Level Metrics

`feeder_eval_results.csv` and `.json` contain one row per evaluated
policy/seed/scenario episode, with at least:

- policy, seed, scenario, target feeder area;
- total requests and steps;
- served and missed request counts/rates;
- invalid and fallback action counts/rates;
- total and mean reward;
- mean and maximum stress;
- voltage, line, transformer, and OPF infeasibility counts;
- mean and total curtailment;
- mean and total feasible energy;
- truth-level and label-source counts;
- average and minimum valid-action counts;
- selected-action distribution.

Request-level decision details may be retained in JSON or an additional
diagnostic file, but are not required to enlarge the CSV contract.

## Aggregation And Statistics

The exporter produces:

- `per_seed_metrics.csv`
- `per_scenario_metrics.csv`
- `summary_metrics.json`
- `statistical_summary.json`
- `scenario_config.json`
- `run_metadata.json`

For numeric policy metrics, report mean, standard deviation, median, minimum,
maximum, sample count, and:

```text
95% CI = mean +/- 1.96 * std / sqrt(n)
```

Comparisons include percent improvement versus random, comparison versus
weighted, checkpoint reward recovery versus weighted, per-seed paired
differences, and the six core grid-metric wins.

Zero-baseline percentage comparisons must be represented as unavailable rather
than divided by zero. Absolute differences remain available.

## Composite Scores

Search selection uses a documented, deterministic composite:

```text
overall_thesis_score =
    grid_safety_score + service_score + cost_score
```

The primary feeder composite uses normalized checkpoint improvements against
random:

- grid safety rewards lower mean stress, voltage violations, line overloads,
  transformer overloads, OPF infeasibility, and curtailment;
- service rewards higher served rate and feasible energy and penalizes invalid
  or fallback actions;
- cost is zero when direct feeder cost is unavailable.

Each component and its inputs are exported. Scores must be bounded or
zero-baseline safe so a near-zero denominator cannot dominate selection.

Secondary app cost metrics never alter the primary feeder grid or service
scores. If cost evidence is available, it is reported separately and may be
used only for a clearly labeled secondary cost-service comparison.

## Transparent Search

With `--keep-searching`, the exporter evaluates deterministic search runs until
the checkpoint wins at least four of the six core metrics against random or
`--max-search-runs` is reached.

Every attempt exports:

```text
search_runs/search_run_<n>/summary_metrics.json
search_runs/search_run_<n>/feeder_eval_results.csv
search_runs/search_run_<n>/scenario_config.json
```

Top-level search outputs are:

- `search_summary.csv`
- `search_summary.json`
- `selected_run_reason.txt`

Selection uses only the declared composite score, with a stable tie-break rule:
more core grid wins, then lower checkpoint fallback count, then lower run
number. The selected result is labeled exploratory whenever more than one
search run was attempted.

Top-level reports also include pooled policy metrics across every attempted
run. The selected run is never presented as the only observed evidence.

If no run meets the target, the report states:

> The tested checkpoint did not demonstrate the target advantage under the
> evaluated stress scenarios.

The best valid composite result is still exported without claiming a pass.

## Secondary App/Runtime Evidence

App/runtime evidence is optional and separately labeled:

```text
secondary_app_cost_evidence/
```

It may contain estimated cost, duration, distance, wait time, price, no-fallback
metadata, and forecast smoke metadata for:

- `weighted_score`
- `cheapest`
- `fastest`
- `closest`
- `rl_maskable_ppo_feeder`

The implementation may duplicate small, stable helper logic from the existing
app exporter. It should import existing helpers only if doing so is
side-effect-light and keeps the evidence boundary obvious.

App recommendation success rate is not included in the feeder performance
table, feeder composite, core advantage target, or primary thesis claim.
`cost_service_summary.json` and cost figures are generated only when genuine
cost data is available.

When cost comes only from this secondary path, reports label it as secondary
user-cost context. It is not mixed into feeder grid-performance conclusions or
used to imply that the feeder checkpoint directly optimized app cost.

## Reports And Claims

Generate:

- `thesis_feeder_rl_evaluation_report.md`
- `thesis_claims_safe_summary.md`

The main report covers configuration, replay provenance, policy results,
grid-safety comparisons, service results, statistics, optional secondary cost
evidence, search attempts, selected-run rationale, pooled evidence, figures,
thesis-safe wording, and limitations.

Claims are generated from actual exported metrics. Strong wording is emitted
only when supported. Balanced or negative wording is emitted when weighted
remains stronger or the random-advantage target is not met.

`thesis_claims_safe_summary.md` must always contain exactly one applicable
headline category:

- a strong supported claim;
- a balanced claim;
- a negative/unmet-target claim.

The headline claim section must never be blank, even when some metrics are
unavailable.

Required limitations are:

- offline recorded feeder replay;
- `area_pf` / `area_reuse` truth;
- not live DigitalTwin closed-loop;
- not MARL;
- forecast metadata/smoke only;
- no forecast-to-RL feature injection;
- app/runtime benchmark is secondary.

## Figures

Use Matplotlib with the `Agg` backend. Each figure is a separate plot, not a
subplot. Required figures are:

- `figures/summary_table.png`
- `figures/grid_safety_improvement_vs_random.png`
- `figures/violation_counts_by_policy.png`
- `figures/opf_infeasible_by_policy.png`
- `figures/mean_stress_by_policy.png`
- `figures/curtailment_by_policy.png`
- `figures/feasible_energy_by_policy.png`
- `figures/reward_by_policy.png`
- `figures/duration_by_policy.png`
- `figures/distance_by_policy.png`
- `figures/service_quality_by_policy.png`
- `figures/invalid_and_fallback_actions.png`
- `figures/served_vs_missed_requests.png`
- `figures/per_seed_reward_distribution.png`
- `figures/checkpoint_vs_random_per_seed.png`
- `figures/checkpoint_vs_weighted_per_seed.png`

If genuine cost data exists, also generate:

- `figures/user_cost_by_policy.png`
- `figures/cost_grid_tradeoff.png`

Feeder figures with unavailable direct feeder duration or distance data must
be labeled as unavailable rather than populated from app evidence. Secondary
app duration and distance figures may use those names only inside the
`secondary_app_cost_evidence/` directory.

## CLI

Support:

- `--mode quick|thesis|stress`
- `--seed-start`
- `--seed-count`
- `--duration-hours`
- `--scenario-count`
- `--output-dir`
- `--checkpoint-path`
- `--feeder-rl-data-dir`
- `--policies random,weighted,checkpoint`
- `--stress-profile`
- `--require-replay-covered-area`
- `--strict`
- `--keep-searching`
- `--max-search-runs`
- `--target-rl-advantage`

Boolean replay-area behavior should have an explicit default matching the
required replay-backed evaluation and remain visible in `scenario_config.json`.

## Strict Validation

Strict mode validates:

- required feeder artifacts and final checkpoint exist;
- action catalog and checkpoint observation shape remain compatible;
- replay rows satisfy `area_pf` minimum truth and exclude adapter proxies;
- replay-covered areas are available;
- mode minimum seeds and unique request counts are met;
- every requested policy produces rows for the same request sets;
- checkpoint inference runs;
- checkpoint invalid and fallback counts are zero;
- all required JSON, CSV, Markdown, and unconditional PNG outputs exist;
- exported JSON is parseable and CSV files have rows.

`--target-rl-advantage` records target status after all evidence has been
exported. An unmet scientific target is a valid benchmark result and does not
by itself cause failure. The flag never changes metrics or selection.

## Testing

Create:

```text
tests/verification/test_feeder_rl_thesis_evaluation.py
```

Focused tests cover:

- scenario definitions and deterministic transformations;
- identical request sets across policies;
- mode minimums;
- metric aggregation and confidence intervals;
- zero-baseline comparisons;
- core grid-win counting;
- composite score calculation;
- transparent search selection and tie-breaking;
- negative thesis-safe wording when the target is unmet;
- feeder/app evidence separation;
- required output and figure generation using synthetic rows;
- strict validation failures.

The checkpoint-backed quick benchmark provides end-to-end verification after
the focused tests pass. Full repo tests, the PR 4 no-fallback verifier, and the
PR 5 forecast verifier remain regression checks.

## Implementation Phases

Implementation proceeds in this order:

1. Phase A: pure helper functions and synthetic-row tests.
2. Phase B: exporter scaffold and output-file generation.
3. Phase C: real feeder evaluator integration.
4. Phase D: transparent search.
5. Phase E: report and figure generation.
6. Phase F: focused, full-suite, quick, thesis, stress, PR 4, and PR 5
   verification commands.

The first implementation remains one script with focused helper functions and
one focused test file. Production modules are extracted only if direct testing
of the script becomes materially difficult.

## Non-Goals

PR 6.1 does not:

- retrain or replace the checkpoint;
- change feeder observations or rewards;
- inject forecast features into RL;
- change app/API/mobile response schemas;
- implement live PF/OPF control;
- implement MARL;
- conceal underperformance or manually choose favorable seeds.
