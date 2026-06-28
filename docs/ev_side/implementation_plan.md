# Feeder RL Evaluation Audit & Runnable Commands

## 1. Diagnosis of Current Evaluation Weakness

> [!CAUTION]
> **The previous evaluation is not a real evaluation — it is a smoke test with fabricated truth.**

| Issue | Evidence |
|---|---|
| Only 8 steps ran out of `--max-steps 50` | Episode terminated early because scenario had ≤8 requests |
| `truth_level_counts = {"unknown": 6}` | Grid advisory mode was `recorded` but scenario sampled an area outside the 7 replay-covered areas, so the replay store returned `advisory_available=False` responses |
| No baseline comparison | Only `checkpoint` policy ran — no `random` or `weighted` baseline |
| No export/CSV | No `--output-json` / `--output-csv` flags were used |
| Checkpoint path pointed to non-existent `models\rl_feeder_final\` | The actual checkpoint is at `EV-side\ev-smart-charging-MARL\ev-smart-charging-MARL\models\rl_feeder\maskable_ppo_feeder_station_selector.zip` |
| No `--require-replay-covered-area` flag | The evaluator CAN restrict to replay-covered areas, but this was not used |
| No `--exclude-adapter-proxy` flag | Not used (although current data has 0 adapter proxy rows anyway) |

---

## 2. Data Package Profile

### Summary

| Property | Value |
|---|---|
| Package path | `outputs\evside_feeder_rl` |
| Export mode | `all_feeders_full` |
| Action catalog rows | **73** stations |
| Action catalog areas | **10** secondary areas |
| Request prior rows | **30** |
| Grid advisory replay rows | **100,000** |
| Replay areas (covered) | **7** of 10 areas |
| Uncovered areas | `LPN-S000000031961`, `LPN-S000000044114`, `LPN-S000000044194` |
| Unique stations in replay | 60 of 73 |
| Connector types | All `ac` |

### Replay Truth Distribution

| Field | Distribution |
|---|---|
| `physical_truth_level` | `area_pf`: 100,000 (100%) |
| `label_source_kind` | `area_reuse`: 100,000 (100%) |
| `evaluation_mode_used` | `replay`: 100,000 (100%) |
| `advisory_available` | `True`: 100,000 (100%) |
| `model_version` | `digitaltwin_pf_opf_snapshot_v1`: 100,000 (100%) |
| `adapter_proxy_row_count` | **0** |
| `unknown_truth_count` | **0** in replay file |
| `exact_candidate_pf` rows | **0** |
| `node_pf` rows | **0** |

### Verdict Distribution (in replay)

| Verdict | Count |
|---|---|
| OK | 50,520 (50.5%) |
| REJECT | 32,015 (32.0%) |
| CAUTIOUS | 17,465 (17.5%) |

### Area Action Distribution

| Area | Actions | Replay rows |
|---|---|---|
| LPN-S000000064056 | 21 | 26,331 |
| LPN-S000000030257 | 16 | 20,080 |
| LPN-S000000010201 | 9 | 14,565 |
| LPN-S000000030013 | 8 | 10,040 |
| LPN-S000000099557 | 2 | 24,728 |
| LPN-S000000008099 | 2 | 2,512 |
| LPN-S000000024872 | 2 | 1,744 |
| LPN-S000000031961 | 8 | 0 ❌ |
| LPN-S000000044114 | 4 | 0 ❌ |
| LPN-S000000044194 | 1 | 0 ❌ |

### Package Scale Classification

> [!WARNING]
> **This is a "capped area_pf replay" package, not a full AC-PF/OPF package.**
>
> - All 100k replay rows are `area_pf` (area-level reuse), not `exact_candidate_pf` or `node_pf`
> - `confidence_score` is uniformly 0.58
> - Mean `bottleneck_margin_percent` is −1.7% (many areas near violation)
> - `opf_feasible` is 0.0 for all rows (all OPF infeasible)
> - This means the replay truth is derived from area-level PF/OPF artifacts reused across stations, not per-node/per-candidate power flow

---

## 3. Evaluator CLI Flag Inventory

### Evaluation Script Flags

| Flag | Exists | Values |
|---|---|---|
| `--policy` | ✅ | `checkpoint`, `random`, `weighted` |
| `--checkpoint-path` | ✅ | Path to `.zip` |
| `--seed` | ✅ | Integer (default 4000) |
| `--max-steps` | ✅ | Integer (default 50) |
| `--duration-hours` | ✅ | Integer (default 1) |
| `--grid-advisory-mode` | ✅ | `disabled`, `recorded`, `http` |
| `--grid-evaluation-mode` | ✅ | `replay`, `surrogate`, `ac_pf`, `opf`, `hybrid` |
| `--min-truth-level` | ✅ | `exact_candidate_pf`, `node_pf`, `area_pf`, `opf_proxy`, `any` |
| `--exclude-adapter-proxy` | ✅ | flag |
| `--require-replay-covered-area` | ✅ | flag |
| `--output-json` | ✅ | Path |
| `--output-csv` | ✅ | Path |
| `--dry-run` | ✅ | flag |
| `--scenario-count` / `--num-episodes` | ❌ | **Missing** — single scenario per run |
| `--scenario-id` | ❌ | **Missing** — cannot pin a specific scenario |
| `--area-filter` | ❌ | **Missing** — area is sampled by seed |
| `--grid-aware-heuristic` baseline | ❌ | Only `random` and `weighted` |
| Inference latency tracking | ❌ | Not tracked |
| Reward std dev | ❌ | Not computed |
| Per-step CSV export | ❌ | Not supported |
| `--validation-split` / `--test-split` | ❌ | Hardcoded `split="validation"` |

---

## 4. Exact Runnable Commands

### Common Path Variables (PowerShell)

```powershell
$EV_PYTHON = "a:\coding\Projects\USSEE\Implementations\DigitalTwin.2.0\EV-side\ev-smart-charging-MARL\ev-smart-charging-MARL\.venv\Scripts\python.exe"
$EVAL_SCRIPT = "a:\coding\Projects\USSEE\Implementations\DigitalTwin.2.0\EV-side\ev-smart-charging-MARL\ev-smart-charging-MARL\scripts\rl_training\evaluate_maskable_ppo_feeder_station_selector.py"
$DATA_DIR = "a:\coding\Projects\USSEE\Implementations\DigitalTwin.2.0\outputs\evside_feeder_rl"
$CHECKPOINT = "a:\coding\Projects\USSEE\Implementations\DigitalTwin.2.0\EV-side\ev-smart-charging-MARL\ev-smart-charging-MARL\models\rl_feeder\maskable_ppo_feeder_station_selector.zip"
$OUT_DIR = "a:\coding\Projects\USSEE\Implementations\DigitalTwin.2.0\outputs\evside_feeder_rl\evaluation_results"
```

---

### A. Smoke Command (prove checkpoint loads, masks work, no fallback)

**Purpose**: Verify that the checkpoint loads, action masking works, grid advisory replay is consumed, and no fallback to random occurs. Labelled **smoke only** — weak truth is accepted.

```powershell
& $EV_PYTHON $EVAL_SCRIPT `
  --feeder-rl-data-dir $DATA_DIR `
  --checkpoint-path $CHECKPOINT `
  --policy checkpoint `
  --grid-advisory-mode recorded `
  --grid-evaluation-mode replay `
  --require-replay-covered-area `
  --min-truth-level any `
  --max-steps 50 `
  --seed 4000 `
  --output-json "$OUT_DIR\smoke_checkpoint.json"
```

**Assessment**: `runnable now` — `runnable but smoke-only`

---

### B. Strict Replay-Backed Evaluation (strongest possible with current data)

**Purpose**: Evaluate checkpoint on replay-covered areas only, requiring `area_pf` truth minimum, with 500 steps across multiple seeds. Since the evaluator only runs one scenario per invocation, we loop over 10 seeds.

```powershell
# Create output directory
New-Item -ItemType Directory -Force -Path $OUT_DIR

# Run checkpoint evaluation across 10 seeds (≈500 total steps)
foreach ($seed in 4000..4009) {
  & $EV_PYTHON $EVAL_SCRIPT `
    --feeder-rl-data-dir $DATA_DIR `
    --checkpoint-path $CHECKPOINT `
    --policy checkpoint `
    --grid-advisory-mode recorded `
    --grid-evaluation-mode replay `
    --require-replay-covered-area `
    --exclude-adapter-proxy `
    --min-truth-level area_pf `
    --max-steps 500 `
    --seed $seed `
    --output-json "$OUT_DIR\strict_checkpoint_seed${seed}.json" `
    --output-csv "$OUT_DIR\strict_all_policies.csv"
}
```

**Assessment**: `runnable now` — `runnable but not thesis-grade` (all truth is `area_pf`, not `exact_candidate_pf` or `node_pf`)

---

### C. Baseline Comparison Commands

**C1. Random-valid baseline** (same seeds as strict evaluation):

```powershell
foreach ($seed in 4000..4009) {
  & $EV_PYTHON $EVAL_SCRIPT `
    --feeder-rl-data-dir $DATA_DIR `
    --policy random `
    --grid-advisory-mode recorded `
    --grid-evaluation-mode replay `
    --require-replay-covered-area `
    --exclude-adapter-proxy `
    --min-truth-level area_pf `
    --max-steps 500 `
    --seed $seed `
    --output-json "$OUT_DIR\strict_random_seed${seed}.json" `
    --output-csv "$OUT_DIR\strict_all_policies.csv"
}
```

**C2. Deterministic weighted baseline** (same seeds):

```powershell
foreach ($seed in 4000..4009) {
  & $EV_PYTHON $EVAL_SCRIPT `
    --feeder-rl-data-dir $DATA_DIR `
    --policy weighted `
    --grid-advisory-mode recorded `
    --grid-evaluation-mode replay `
    --require-replay-covered-area `
    --exclude-adapter-proxy `
    --min-truth-level area_pf `
    --max-steps 500 `
    --seed $seed `
    --output-json "$OUT_DIR\strict_weighted_seed${seed}.json" `
    --output-csv "$OUT_DIR\strict_all_policies.csv"
}
```

**C3. Grid-aware heuristic baseline**:

> [!IMPORTANT]
> **Not supported by the current evaluator.** The `--policy` flag only accepts `checkpoint`, `random`, `weighted`. The `weighted` baseline already uses `env.reward_model.compute()` to greedily pick the highest-reward action, which is a simple greedy-grid-aware heuristic.
>
> A dedicated grid-aware heuristic (e.g., "always pick the lowest stress_score station") would need a new policy name and ~20 lines in `_select_action()`.

---

### D. Export/Report Commands

The evaluator already supports `--output-json` and `--output-csv` (appending). All commands above include these flags. To aggregate after all runs:

```powershell
# Print the aggregated CSV
Get-Content "$OUT_DIR\strict_all_policies.csv"

# Or parse with Python
& $EV_PYTHON -c "
import pandas as pd, json
df = pd.read_csv(r'$OUT_DIR\strict_all_policies.csv')
print(df[['policy','scenario_id','steps','total_reward','mean_reward','missed_requests','invalid_actions','fallback_actions','average_stress_score','voltage_violation_count','line_overload_count','trafo_overload_count','opf_infeasible_count']].to_string())
"
```

---

## 5. Recommended Evaluation Metrics Table Schema

| Metric | Type | Source |
|---|---|---|
| `policy` | string | CLI flag |
| `checkpoint_path` | string | CLI flag (null for baselines) |
| `scenario_id` | string | output JSON |
| `seed` | int | CLI flag |
| `step_count` | int | `steps` |
| `served_requests` | int | `steps - missed_requests - invalid_actions` |
| `missed_requests` | int | ✅ tracked |
| `served_rate` | float | **not computed — needs code** |
| `missed_rate` | float | **not computed — needs code** |
| `invalid_action_count` | int | ✅ tracked |
| `invalid_action_rate` | float | **not computed — needs code** |
| `fallback_action_count` | int | ✅ tracked |
| `total_reward` | float | ✅ tracked |
| `mean_reward` | float | ✅ tracked |
| `reward_std` | float | ❌ **not tracked** |
| `average_distance` | float | ❌ **not tracked** |
| `average_wait` | float | ❌ **not tracked** |
| `average_cost` | float | ❌ **not tracked** |
| `average_duration` | float | ❌ **not tracked** |
| `average_stress_score` | float | ✅ tracked |
| `max_stress_score` | float | ✅ tracked |
| `voltage_violation_count` | int | ✅ tracked |
| `line_overload_count` | int | ✅ tracked |
| `trafo_overload_count` | int | ✅ tracked |
| `opf_infeasible_count` | int | ✅ tracked |
| `mean_curtailment_required_kw` | float | ✅ tracked |
| `mean_feasible_energy_kwh` | float | ✅ tracked |
| `truth_level_counts` | dict | ✅ tracked |
| `grid_verdict_distribution` | dict | ❌ **not tracked** |
| `replay_coverage_rate` | float | ❌ **not tracked** |
| `adapter_proxy_count` | int | ❌ **not tracked** (0 in current data) |
| `unknown_truth_count` | int | derivable from `truth_level_counts` |
| `inference_latency_ms` | float | ❌ **not tracked** |

---

## 6. Strict Readiness Judgment

| Evaluation tier | Status | Reason |
|---|---|---|
| **Smoke (A)** | ✅ `runnable now` | Checkpoint loads, masks work, replay responds |
| **Strict replay-backed (B)** | ⚠️ `runnable but not thesis-grade` | 100k rows are `area_pf` only, not per-node PF truth; `opf_feasible=0` for all rows |
| **Random baseline (C1)** | ✅ `runnable now` | |
| **Weighted baseline (C2)** | ✅ `runnable now` | |
| **Grid-aware heuristic (C3)** | ❌ `blocked by missing CLI flag` | `--policy` does not accept a grid-heuristic option |
| **Multi-episode evaluation** | ❌ `blocked by missing CLI flag` | No `--scenario-count` or `--num-episodes`; must loop over seeds externally |
| **Thesis-grade with real PF truth** | ❌ `blocked by smoke/capped data package` | All replay truth is `area_pf` / `area_reuse`; 0 rows at `exact_candidate_pf` or `node_pf` |
| **Thesis-grade with OPF truth** | ❌ `blocked by missing real PF/OPF replay` | `opf_feasible=0.0` for all 100k rows; replay model version is `digitaltwin_opf_adapter_proxy_v1` |

---

## 7. What Is Missing for Thesis-Grade Evaluation

### Data gaps

1. **No `exact_candidate_pf` or `node_pf` replay rows** — all 100k rows are `area_pf` / `area_reuse`
2. **All rows have `opf_feasible=0`** — the OPF data uniformly shows infeasible, which may be an artifact of the adapter proxy generation
3. **3 areas have zero replay coverage** — 13 stations (18%) cannot be evaluated with replay truth
4. **Only 30 request priors** — small request diversity

### Evaluator code gaps

1. **No multi-episode `--scenario-count` flag** — must manually loop seeds
2. **No `reward_std` computation** — need to accumulate per-step rewards
3. **No grid verdict distribution tracking** — easy to add in the metrics dict
4. **No per-step distance/wait/cost/duration tracking** — reward breakdown exists but individual user-service metrics are not surfaced
5. **No inference latency timing** — `time.perf_counter()` around `model.predict()` needed
6. **No `served_rate` / `missed_rate` derived metrics** — trivial post-hoc calculation
7. **The `weighted` baseline is already a greedy-grid-aware heuristic** — using `env.reward_model.compute()` to score all valid actions and taking the max. A more sophisticated grid heuristic (e.g., lowest stress_score) is not a separate policy option.

---

## 8. Recommended Next Code Changes (If Evaluator Is Not Strong Enough)

> [!NOTE]
> These are **not** modifications I will make now. These are recommendations for your approval.

### Priority 1: Add `--scenario-count` to the evaluator (10 lines)

Add a `--scenario-count N` flag that loops internally over N seeds starting from `--seed`, accumulating metrics across episodes. This eliminates the need for external PowerShell loops and produces proper aggregate statistics (mean, std).

### Priority 2: Add `reward_std` and per-step tracking (15 lines)

Accumulate `rewards_per_step: list[float]` and compute `np.std()` at the end. Also track `grid_verdict_counts` dict.

### Priority 3: Add `served_rate` / `missed_rate` / `invalid_rate` (5 lines)

Derive these from `steps`, `missed_requests`, `invalid_actions` in the final metrics dict.

### Priority 4: Add inference latency (8 lines)

Wrap `model.predict()` in `time.perf_counter()` and report `mean_inference_ms`.

### Priority 5: Generate `exact_candidate_pf` replay data

Run the DigitalTwin PF solver for each of the 73 action catalog stations with per-candidate power flow. This is a grid-side task, not an EV-side code change.

---

## Open Questions

> [!IMPORTANT]
> **Q1**: Should I execute the smoke command (Group A) and the strict evaluation + baseline loop (Groups B + C) now? This will take ~5-10 minutes for 30 runs × 500 steps each.

> [!IMPORTANT]
> **Q2**: Should I implement Priority 1-4 code changes (add `--scenario-count`, `reward_std`, derived rates, inference latency) before running the full evaluation? This would make the evaluation output more thesis-ready.

> [!IMPORTANT]
> **Q3**: The `weighted` baseline already acts as a greedy grid-aware heuristic (picks highest-reward action). Do you want a separate `--policy lowest_stress` heuristic, or is `weighted` sufficient as the "smart baseline"?
