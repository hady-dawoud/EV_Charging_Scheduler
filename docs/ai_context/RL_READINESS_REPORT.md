# RL Readiness Report

## 2026-06-13 Post-Merge Runtime Readiness

Current verdict: the repo has an RL/grid-advisory scaffold and tracked checkpoints, but it is not fully MARL-ready and the feeder checkpoint path is not fully runnable from repo-local artifacts alone.

What is ready:

- The older single-agent Dundee station-selection scaffold exists under `packages/ev_core/src/ev_core/rl/`.
- The newer feeder public-EV scaffold exists under `packages/ev_core/src/ev_core/rl_feeder/`.
- Grid-advisory contracts, replay lookup, disabled/recorded/http/runtime-http clients, and feature mapping exist under `packages/ev_core/src/ev_core/grid_advisory/`.
- Checkpoint-backed recommender policies exist:
  - `rl_maskable_ppo` in `recommender/rl_policy.py`
  - `rl_maskable_ppo_feeder` in `recommender/feeder_rl_policy.py`
- `PolicyRegistry` registers both checkpoint-backed policy names along with deterministic policies.
- The current mobile/API response contracts remain unchanged.
- RL checkpoints are present in this checkout:
  - `models/rl/maskable_ppo_station_selector.zip`
  - `models/rl_feeder/maskable_ppo_feeder_station_selector.zip`
  - `models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip`

What is not ready:

- Full MARL is not implemented.
- The default app/API policy is still deterministic `weighted_score` unless runtime configuration selects another registered policy.
- The feeder policy cannot do true checkpoint inference from the normal app flow until the runtime builds and passes `feeder_observation`, `feeder_action_mask`, and `feeder_station_ids`.
- The feeder runtime data package is missing from this checkout:
  - `data/processed/evside_feeder_rl/manifest.json`
  - `data/processed/evside_feeder_rl/feature_stats.json`
  - `data/processed/evside_feeder_rl/feeder_ev_action_catalog.csv` or `.parquet`
  - `data/processed/evside_feeder_rl/feeder_request_priors.csv` or `.parquet`
  - `data/processed/evside_feeder_rl/feeder_grid_advisory_replay.csv` or `.parquet`
- `outputs/evside_feeder_rl/`, the fallback/default local path used by feeder training scripts outside a DigitalTwin parent checkout, is also missing.
- `sb3_contrib`, `stable_baselines3`, `torch`, and `gymnasium` remain optional runtime/training dependencies rather than base app/API dependencies.

Forecasting status:

- Forecasting artifacts are present under `models/forecasting/load_kw_30min/`.
- The current runtime still uses `ForecastProvider` interfaces and table-backed/zero providers; no code path loads `lstm_huber_load_kw_30min.keras` into recommendations.
- A pretrained RL checkpoint cannot directly benefit from newly appended forecast observation features unless it was trained with that same observation shape.
- The first valid forecasting smoke path should either expose forecasts without changing recommendations, use forecast output as a separate heuristic/future-congestion term, or retrain a small RL model with forecast features.

Recommended next integration path:

1. Decide the canonical repo-local feeder data package path and copy or generate the missing feeder package there.
2. Add a feeder observation-context adapter for app/runtime recommendations.
3. Smoke-test `rl_maskable_ppo_feeder` with `RL_FEEDER_CHECKPOINT_PATH` and deterministic fallback enabled.
4. Decide whether tracked model artifacts should remain normal Git files or move to Git LFS/release assets.
5. Keep MARL out of the app path until single-agent and feeder checkpoint paths are reproducible with explicit artifacts and fallback tests.

## Verification Snapshot

- Branch verified: `MARL`
- Pre-flight after merge: clean working tree on `MARL`
- Full test suite before PR2: `192 passed`
- Verified scripts:
  - `scripts/verify_runtime_smoke.py`
  - `scripts/verify_dynamic_pricing.py`
  - `scripts/verify_dundee_tariff_pricing.py`
  - `scripts/verify_synthetic_live_requests.py --count 10 --timestamp 2024-06-10T12:00:00`
  - `scripts/verify_app_runtime_integration.py`
- OSMnx graph status: `data/processed/routing/dundee_drive.graphml` is not present locally, so OSMnx remains optional and is not the RL default.

## PR2 Status

PR2 now adds the fixed-seed RL preparation layer without adding training:

- `ev_core.rl.contracts`: frozen scenario/evaluation dataclasses
- `ev_core.rl.scenarios`: deterministic train/validation/test scenario sampling plus synthetic-live scenario request generation
- `ev_core.rl.baselines`: `random_valid` valid-action baseline helper
- `ev_core.rl.evaluation`: lightweight deterministic-baseline evaluation harness
- `ev_core.rl.forecast_features`: placeholder forecast feature contract for future observation work

This PR still does not add Gymnasium, Stable-Baselines3, MaskablePPO, MARL, or long-running training code.

## PR3 Status

PR3 now adds the first Gymnasium-compatible RL environment skeleton:

- `ev_core.rl.env.DundeeStationSelectionEnv`
- `ev_core.rl.observations.ObservationBuilder`
- `ev_core.rl.action_mask.build_station_action_mask(...)`
- `ev_core.rl.rewards.StationSelectionReward`

Scope and constraints:

- single-agent station selection only
- masked discrete actions over a deterministic station list
- fixed-size flat observation vector
- first-pass reward contract
- decision-level skeleton for now

This PR still does not add MaskablePPO training, Stable-Baselines3, `sb3-contrib`, MARL, or PettingZoo.

## PR4 Status

PR4 now adds the first offline Dundee RL training boundary under `ev_core.rl_training`:

- `offline_station_selection_env.py` wraps `ev_core.rl.env.DundeeStationSelectionEnv` instead of forking env logic
- `scenario_factory.py` builds reproducible Dundee train/validation/test scenario bundles from `RLScenarioSampler` and `RLTrainingConfig`
- `data_adapter.py` loads Dundee bundle counts and request-generation inputs without runtime-storage coupling
- `rollout.py` runs random-valid, fixed-action, and deterministic recommendation-policy rollouts without SB3
- `metrics.py` summarizes rollout outputs for quick offline evaluation

This PR still does not add MaskablePPO training, Stable-Baselines3, `sb3-contrib`, MARL, or checkpoint-backed runtime inference.

## Current Implementation Status

The current system is RL-adjacent but still deterministic at decision time.

- Synthetic-live request generation is implemented and verified through `SyntheticLiveRequestGenerator` plus runtime-path verification.
- CP-aware availability is implemented in `DundeeEnv` using connector compatibility and available compatible-port checks.
- Vehicle profiles are implemented with battery, AC, and DC constraints and already affect duration and connector-power estimates.
- Dynamic pricing is implemented and verified, including transformer-headroom and congestion overlays.
- Dundee charger-class base tariffs are implemented and verified for AC standard, AC fast, rapid, and ultra rapid classes.
- Topology scenarios are implemented, including calibrated realistic and stress variants.
- Routing is provider-based. `simple_distance` is the working default. Optional OSMnx support exists behind the same seam and falls back safely when the graph/backend is unavailable.
- Deterministic baselines are implemented: `weighted_score`, `closest`, `cheapest`, `fastest`, and `overload_aware`.
- Runtime, API, and dashboard integration are already present and verified without changing response shape.

## Is RL The Next Correct Step?

Verdict: `Yes`, but not “trainer-first”.

Single-agent masked RL is the correct next major step after this readiness pass, because the simulator now has enough state realism to justify learning-based dispatch. The blockers are not missing pricing/routing features anymore; they are evaluation and data-generation controls.

Current blockers before RL implementation:

- Demand realism needs explicit scenario scaling because historical average demand is well below the infrastructure capacity of the current 90-chargepoint topology.
- There is no dedicated evaluation harness yet for fixed-seed comparisons across deterministic baselines and future RL policies.
- There is no episode-level scenario sampler yet for controlled variation across day type, time window, demand multiplier, vehicle mix, and topology scenario.
- Observation, reward, and masking contracts are not yet frozen in code.

Recommended immediate next implementation PR:

- Add an RL evaluation harness plus scenario sampler first.
- Keep training out of that PR.
- Use that PR to lock fixed-seed train/validation/test scenario generation, baseline evaluation, and RL environment contracts.

Status update:

- This PR2 has now done that first harness/sampler step.
- PR3 has now added that Gymnasium single-agent masked environment skeleton.
- PR4 now exposes a clean offline-training boundary around that env for Colab/Kaggle-style use without touching app/runtime response contracts.
- The next PR should add MaskablePPO training and baseline-evaluation scripts.

## Runtime Recommender Plug-In Architecture

Learned inference should be added as a recommender policy, not as a replacement for API/mobile/dashboard contracts.

Target path:

```text
offline training
-> checkpoint available under the agreed artifact path
-> RL policy class loads checkpoint
-> policy registered in PolicyRegistry
-> RecommendationService can select it like other policies
-> fallback to deterministic policy if checkpoint/context/dependencies are missing
```

The first checkpoint-backed policies are single-agent MaskablePPO hooks. MARL should come later, after single-agent/feeder training, evaluation, artifact loading, and fallback behavior are stable. Checkpoint-backed policies should consume the same candidate contexts built by `DundeeEnv`/`CandidateBuilder` or explicitly documented feeder observation context and return the same `RecommendationOption` / `RecommendationResponse` shape already used by the app.

Offline training can run on Colab/Kaggle if it installs this repo and imports the repo environment/scenario sampler directly. The current branch tracks selected model artifacts in Git; future PRs still need to decide whether continued checkpoint storage should use normal Git, Git LFS, release assets, or an external artifact store.

## Why Masked RL, Not Plain DQN

The action space is naturally “choose a station” for each decision point, so a discrete action formulation is appropriate. The problem is that many stations are invalid at any given time.

Invalid actions arise from:

- charger incompatibility
- no compatible free chargepoint
- deadline infeasibility
- transformer headroom limits
- station/runtime access constraints

A plain DQN-style setup without masking would spend too much effort exploring invalid station choices and would need awkward penalty shaping to learn basic feasibility. Action masking removes impossible moves directly and makes the policy learn among feasible stations only.

Recommended first RL baseline:

- `MaskablePPO`

It matches the discrete masked action space better than plain DQN for this stage and is the right first baseline before considering more complex multi-agent work.

## Recommended RL Environment Shape

Action space:

- `Discrete(num_stations)`

Action mask:

- `1` for stations that are currently valid
- `0` for stations that are invalid due to compatibility, no available compatible connector, infeasible finish window, access restrictions, or transformer/power constraints

Recommended observation vector contents:

- request features
  - requested energy
  - latest finish slack
  - charger preference
  - vehicle battery / AC max / DC max
  - current location or derived origin-zone signal
- global environment features
  - simulated time-of-day
  - weekday/weekend
  - demand multiplier
  - topology scenario id
  - routing provider flag
- per-station features
  - zone id embedding or index
  - route distance
  - route duration
  - compatible available-port count
  - queue length
  - utilization
  - estimated wait
  - transformer headroom
  - dynamic final price
  - best available connector power

Recommended reward components:

- positive reward for successfully serving the request
- negative reward for missed requests
- negative reward for overload or low-headroom operation
- negative reward for long detours, waiting, or deadline slack consumption
- negative reward for high charging cost when the request preference is cost-sensitive
- optional small imitation-friendly shaping around rank quality versus deterministic baselines

Episode definition:

- one episode = one sampled time window under one sampled scenario package
- recommended first windows: 1h, 3h, 6h, 24h

Reset semantics:

- sample scenario metadata
- select topology scenario
- set replay/synthetic demand controls
- initialize runtime at sampled timestamp and warm-start settings

Step semantics:

- expose one routing/recommendation decision at a time for the current pending external/live request
- apply selected station if valid
- advance the simulator until the next decision point or terminal state

PR3 implementation note:

- the first environment version is decision-level rather than fully closed-loop
- it reuses `DundeeEnv` candidate generation and feasibility logic
- it advances request-by-request and computes reward from the chosen feasible candidate
- full session/queue mutation can be layered in later without replacing the action/observation skeleton

## Baselines To Compare

- `random_valid`
- `weighted_score`
- `closest`
- `cheapest`
- `fastest`
- `overload_aware`
- `MaskablePPO` later

## Routing Recommendation For RL

Use `simple_distance` as the first RL default.

Reasons:

- it is deterministic and already verified
- it is fast enough for large training loops
- it avoids optional graph dependency issues
- it avoids mixed fallback behavior during training

OSMnx should remain optional until route-quality validation improves.

Reasons:

- the local Dundee graph is missing in the current repo state
- OSMnx currently depends on optional local artifacts and optional backends
- fallback-to-simple-distance behavior is safe for runtime, but it is undesirable as hidden transition noise inside RL training
- route realism usefulness has not yet been established strongly enough to make it the training default

## Training Outside Repo

Recommended workflow for Colab/Kaggle or similar external training:

- install the repo in the notebook/runtime environment
- train using the repo’s actual environment and scenario sampler code
- save checkpoints only
- copy checkpoints back into the repo workspace for local evaluation
- evaluate locally with fixed seeds against deterministic baselines

Do not train in a notebook-only fork of the environment that drifts from the repo code. That would make offline evaluation and later integration unreliable.

## Forecasting Placeholder

PR2 adds `ForecastFeatureSnapshot` as a future observation contract only.

- Scenario sampling can already carry a `forecast_profile` field.
- The future RL observation builder can append forecast features later without changing the scenario contract.
- Future MARL feeder/zone agents can consume localized transformer or zone forecast slices from the same contract family.

Current recommendation:

- Background load is optional for pure EV-demand forecasting.
- Background load is required for meaningful grid-headroom forecasting because transformer headroom depends on non-EV load as well as EV demand.

## Baseline Evaluation Scope

PR2 baseline evaluation is intentionally lightweight and request-centric.

- It reuses the existing recommendation path with fixed-seed scenarios.
- It advances scenario time and captures deterministic recommendation-quality metrics.
- It does not yet run a full closed-loop multi-step allocation rollout across all baselines.

This is enough to freeze seed splits, scenario generation, baseline names, and metric contracts before the Gymnasium environment PR.

Status update:

- PR3 now adds that Gymnasium environment skeleton.
- The evaluator remains useful for request-centric baseline comparisons, while the new env freezes the masked observation/action/reward contract for training integration.

## PR3 Environment Skeleton

Observation contract:

- flat `float32` vector
- global request/time features first
- per-station features appended in deterministic station order
- valid-action mask included in per-station features

Action contract:

- `Discrete(num_stations)`
- one action index per deterministic station id
- `action_masks()` / `valid_action_mask()` expose feasible station actions only

Reward contract:

- positive served reward
- stronger penalty for invalid actions
- missed-request penalty when no feasible candidate exists
- small penalties for cost, distance, wait, duration, and low headroom

Routing note:

- `simple_distance` remains the default RL routing provider
- OSMnx remains optional and is not part of the default PR3 environment path

## Monte Carlo Scenario Generation Plan

### Is `SyntheticLiveRequestGenerator` Enough?

Not by itself.

It is good enough as the base request sampler because it already captures:

- historical arrival priors
- zone demand share
- energy and duration priors
- user preference priors
- vehicle profile-aware request fields

It is not yet enough as the full RL episode generator because it does not currently manage episode-level controls such as:

- sampled day type / time window packages
- explicit demand-multiplier curricula
- controllable vehicle profile mixtures
- topology scenario rotation
- background-load / pricing regime rotation
- train/validation/test seed partitions

Recommendation:

- use `SyntheticLiveRequestGenerator` as the base
- add a scenario sampler around it in the next PR
- do not replay old sessions only
- do not train only on overload scenarios

### Recommended Episode Sampling Strategy

Sample each episode from historical priors plus scenario controls:

- sample day type: weekday or weekend
- sample month bucket or season
- sample time window: morning, midday, peak, evening, overnight
- sample topology scenario: default realistic most of the time, stress sometimes
- sample demand multiplier around the historical baseline
- sample vehicle profile mix
- sample background load / pricing regime implicitly through simulator timestamp and scenario selection

Suggested demand-multiplier usage:

- normal curriculum: `1.5x` to `3.0x`
- busy curriculum: `3.0x` to `5.0x`
- stress curriculum: `5.0x+` only as a minority slice

This multiplier guidance is necessary because the current historical average demand is much lower than the available 90-chargepoint capacity.

Suggested vehicle-mix strategy:

- start with current default market-share weights
- later perturb by scenario to overweight small EV, large EV, or van-heavy mixes

Suggested topology strategy:

- default training emphasis on `dundee_synthetic_v1_realistic`
- periodic exposure to default/base topology
- limited exposure to stress topology for robustness, not as the only training mode

Suggested seed split:

- train seeds: `1000-1999`
- validation seeds: `2000-2099`
- test seeds: `3000-3099`

Keep these splits fixed and never reuse test seeds for training or reward tuning.

## Demand Realism Summary

Current repo-backed counts from `scripts/analyze_rl_demand_realism.py`:

- station_count: `35`
- chargepoint_count: `90`
- connector_count: `90`
- total_port_capacity_kw: `3176.0`
- zone_count: `4`
- transformer_count: `8`
- vehicle_profile_count: `4`

Current request-rate summary:

- 2023: `117701` requests, `322.468/day`, `13.436/hour`
- 2024: `90320` requests, `246.776/day`, `10.282/hour`
- blended estimated arrivals_per_hour: `11.859`
- average synthetic-live requested_energy_kwh: `22.738`
- average estimated duration_minutes: `51.525`
- estimated active_cars: `10.2`

Interpretation:

- The repo does in fact have about `90` chargepoints.
- Historical-average demand implies only about `10.2` concurrent active cars.
- That is far below the desired RL operating bands for a 90-chargepoint system.
- RL training should therefore not use raw historical-average demand only, or the policy will mostly train in underutilized conditions.

Utilization bands for 90 chargepoints:

- normal utilization: `30%-60%` -> `27-54` active cars
- busy utilization: `60%-80%` -> `54-72` active cars
- stress utilization: `80%-100%` -> `72-90` active cars

Recommended request counts by horizon:

- 1 hour
  - normal: `31-63`
  - busy: `63-84`
  - stress: `84-105`
- 3 hours
  - normal: `94-189`
  - busy: `189-252`
  - stress: `252-314`
- 6 hours
  - normal: `189-377`
  - busy: `377-503`
  - stress: `503-629`
- 24 hours
  - normal: `755-1509`
  - busy: `1509-2012`
  - stress: `2012-2515`

These episode sizes should be treated as target planning ranges, not default runtime overload settings.

## PR2 Configuration Status

Readiness scaffolding now includes centralized config contracts:
- offline training outputs can be configured via `RLTrainingConfig` (`RL_CHECKPOINT_DIR`, `RL_EVALUATION_DIR`, `RL_TENSORBOARD_DIR`, `RL_FIGURES_DIR`)
- offline scenario construction and headless rollout utilities now live under `ev_core.rl_training`
- `simple_distance` remains the default offline-training routing provider
- the first offline-training wrapper intentionally reuses `DundeeStationSelectionEnv` as the source of truth
- future checkpoint inference can be configured via `RLDeploymentConfig` (`RL_POLICY_CHECKPOINT_PATH`, `RL_POLICY_FAIL_CLOSED`, `RL_FALLBACK_POLICY_NAME`)

What is still intentionally not implemented:
- no full app-flow feeder checkpoint inference without feeder observation context
- no MARL implementation
- no benchmark dependency integration (EV2Gym/SustainGym remain future adapters)
