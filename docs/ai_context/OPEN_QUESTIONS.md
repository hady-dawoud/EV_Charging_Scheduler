# Open Questions

## Runtime Artifacts And Model Loading

- Where should the feeder RL runtime data package live in this repo?
  - Candidate repo-local path: `data/processed/evside_feeder_rl/`.
  - Existing feeder training script fallback path: `outputs/evside_feeder_rl/`.
  - Current truth: neither path exists in this checkout.
  - Decision needed: choose one canonical path for committed/runtime-visible feeder package files and update scripts/config/docs consistently.

- Should RL model zips be committed with Git LFS?
  - Current truth: the RL checkpoint zips are tracked by normal Git.
  - Current truth: `.gitattributes` only configures Git LFS for `data/interim/*.csv`.
  - Decision needed: keep these small checkpoints in normal Git, move them to Git LFS, or publish them as release/external artifacts and keep only placeholders/config in Git.

- Should forecasting artifacts be committed?
  - Current truth: `models/forecasting/load_kw_30min/lstm_huber_load_kw_30min.keras`, scalers, and metadata are tracked by normal Git.
  - Decision needed: keep the selected production/smoke model in Git, move to Git LFS, or use an external model registry/release asset.
  - Decision needed: whether optional comparison models should stay external or be tracked for reproducibility.

- Should forecast output affect `weighted_score` first or only RL after retraining?
  - Current truth: no runtime provider loads the Keras forecasting artifact into recommendations.
  - Constraint: app/API/mobile response shape should remain unchanged.
  - Constraint: a pretrained RL checkpoint cannot safely consume newly appended forecast observation features unless it was trained with that exact feature shape.
  - Decision needed: add forecast as a separate heuristic/future-congestion penalty first, expose forecasts without changing ranking, or retrain a forecast-aware RL smoke model.

- Which exact forecast provider schema should be used?
  - Current provider protocol supports background load, price, and PV series over timestamps.
  - Current trained artifact target is `load_kw_30min`, with 30-minute frequency, `lookback=48`, `feature_count=148`, and one-step horizon.
  - Decision needed: define how runtime 15-minute simulator timestamps map to the 30-minute model, how features are assembled, how scalers are loaded, and whether forecasts are citywide, transformer-level, feeder-level, or station-context features.

- Should `archive/` be the standard local-only staging area for external snapshots?
  - Current truth: `archive/` is ignored by Git.
  - Decision needed: whether artifact-copy instructions should point to `archive/` only for source snapshots, while canonical runtime paths live under `models/` and `data/processed/evside_feeder_rl/`.

## Request Contract

- Is `request_timestamp` required for mobile/live requests?
  - Current truth: `ExternalChargingRequest.request_timestamp` remains required. The backend does not default missing timestamps to server time.
  - Risk: API clients without a client-side timestamp fail validation.
  - Follow-up: decide whether a future API boundary should default missing timestamps while keeping the core contract explicit.

- How should `requested_energy_kwh` mismatch with SOC-derived energy be handled?
  - Resolved first-step policy: if SOC and battery capacity are present, explicit `requested_energy_kwh` must match SOC-derived energy within `0.5` kWh absolute tolerance or `5%` relative tolerance.
  - Missing `requested_energy_kwh` is inferred from SOC and battery when possible.
  - If SOC/battery data is unavailable and energy is missing, the contract still defaults to `20.0` kWh for compatibility.

- What domain validation should be enforced first?
  - First-step validation now enforced: SOC range and ordering, battery capacity `0 < battery_kwh <= 250`, positive requested energy, requested energy not greater than known battery capacity, latest finish after request timestamp, global coordinate bounds, charger type allow-list, and SOC-derived energy consistency.
  - Still open: plausible Dundee location and max request window policy.

- How should vehicle profiles be sourced long term?
  - Current truth: optional `vehicle_profile_id`, `vehicle_max_ac_kw`, and `vehicle_max_dc_kw` are supported on live requests.
  - Current truth: `ev_core.vehicles.profiles` contains a small in-code default catalog; runtime does not depend on a CSV.
  - Current truth: synthetic-live request generation samples these default profiles and populates vehicle fields.
  - Still open: CSV/database-backed profiles, richer market-share data, and profile-specific charging curves.

## Candidate Eligibility

- Should Greenmarket bus charger, car-club, depot, or other restricted/special-purpose stations be public recommendation candidates?
  - Corrected project assumption: the Dundee dataset is treated as a public charging-station dataset.
  - Current truth: `Station` now has access flags and `CandidateBuilder` applies `StationEligibilityFilter` before compatibility/window checks.
  - Current truth: `data/processed/station_access_overrides.csv` is merged by the repository layer when present, making station access data-driven without runtime station-ID hardcoding.
  - Current default: missing station access fields or absent override file are treated as public/unrestricted, preserving existing behavior.
  - Mechanically supported blocks: excluded, non-public, fleet-only, and membership-required stations.
  - `needs_followup` is a manual-review/data-quality flag and does not block recommendations.
  - Current override data keeps all rows public and non-excluded; it records bus/depot/car-club/location concerns as review notes only.
  - Still open: manual verification with external live maps/site data before marking any station restricted.

- Should distance be road routing or simple approximation?
  - Current truth: recommendation distance now goes through an injectable routing-provider seam in `ev_core.routing`.
  - Current truth: the default `SimpleDistanceRoutingProvider` preserves the old behavior exactly: simple lat/lon approximation when coordinates exist, `0.5` km same-zone fallback otherwise, `3.0` km different-zone fallback otherwise.
  - Current truth: an optional offline `OSMnxRoutingProvider` now exists and can use a locally built Dundee drive graph when available.
  - Current truth: if the graph file or OSMnx/NetworkX backend is unavailable, the OSMnx provider falls back to simple-distance behavior by default unless configured fail-closed.
  - Current truth: synthetic-live origins are jittered around station/zone anchors, not sampled from road nodes.
  - Still open: how to compare simple-distance vs OSMnx routing quantitatively, and when to add OSRM service routing behind the same seam.

- How should synthetic-live scenarios evolve?
  - Current truth: `SyntheticLiveRequestGenerator` creates valid `ExternalChargingRequest` objects with `source_type="external_live"` and synthetic-live metadata.
  - Current truth: it uses Dundee historical priors, station/zone distributions, and default vehicle profiles without replaying old sessions.
  - Current truth: PR2 now adds `RLScenarioSampler` and `generate_requests_for_scenario(...)` around the synthetic-live generator with fixed train/validation/test seed ranges and explicit normal/busy/stress scenario contracts.
  - Still open: route-aware origin sampling, richer vehicle-profile priors, scenario catalogs beyond the current defaults, and evaluation-set versioning.

## Dynamic Pricing

- Are the current dynamic pricing multipliers final?
  - Current truth: no. The transformer/congestion multipliers are intentionally simple, deterministic, and explainable first-step simulation coefficients.
  - Current truth: displayed recommendation cost now uses simplified Dundee charger-class base tariffs plus the capped dynamic overlay.
  - Current truth: this is still simulation/display pricing only, not real billing.
  - Current truth: no connection, parking, overstay, or reservation fees are applied.
  - Still open: calibration against stress scenarios, queue sensitivity tuning, and whether future policy/MARL work should consume the same signal directly.

## RL Preparation

- Is the current RL baseline evaluation fully closed-loop?
  - Current truth: no. PR2 baseline evaluation is request-centric and uses the existing recommendation path under fixed-seed scenarios.
  - Current truth: this is enough to lock contracts, seed splits, scenario metadata, and baseline names before Gymnasium work begins.
  - Current truth: PR3 now adds a Gymnasium-compatible masked environment skeleton, but it is still decision-level rather than fully closed-loop queue/session mutation.
  - Current truth: PR4 now wraps that env through `ev_core.rl_training` for offline scenario creation, rollout, and metrics without changing the underlying env semantics.
  - Still open: a true stepwise closed-loop evaluator that uses the same masked environment semantics while mutating runtime sessions and queues.

- Is demand scaling now formalized enough for RL preparation?
  - Current truth: yes for first-step scenario generation. PR2 uses demand realism guidance from the repo data, including the current 35-station / 90-chargepoint topology and the fact that historical average demand is lighter than normal utilization.
  - Current truth: demand multipliers now have explicit curriculum bands: normal `1.5x-3.0x`, busy `3.0x-5.0x`, stress `5.0x+` as a minority slice.
  - Still open: whether those multiplier bands need recalibration after the Gymnasium environment and evaluation harness are running closed-loop.

- How should forecasting plug into RL?
  - Current truth: PR2 adds a `ForecastFeatureSnapshot` placeholder with default `source="none"`.
  - Current truth: forecasting model artifacts are present under `models/forecasting/load_kw_30min/`, but no model-backed `ForecastProvider` loads them into runtime or RL observations yet.
  - Current truth: background load is optional for EV-arrival forecasting, but it is required for true grid-headroom forecasting because transformer headroom depends on non-EV load too.
  - Still open: the exact observation schema for forecast features and whether single-agent RL and future MARL agents should consume the same forecast channels.

- Is the PR3 observation/action/reward contract final?
  - Current truth: no. PR3 freezes a first stable version so training integration can begin.
  - Current truth: the env is single-agent, station-selection, masked discrete action, and fixed-size flat vector observation.
  - Current truth: `simple_distance` remains the default RL routing provider and OSMnx stays optional.
  - Current truth: PR4 keeps `DundeeStationSelectionEnv` as the single source of truth and adds only a thin offline-training wrapper around it.
  - Still open: observation normalization, feature scaling policy, richer per-station features, and reward tuning after first MaskablePPO experiments.

## Routing

- Is OSMnx useful enough to keep for evaluation or future RL routing realism?
  - Current truth: OSMnx support remains optional and default runtime routing is still `simple_distance`.
  - Current truth: PR2 keeps `simple_distance` as the first RL default and does not make OSMnx part of scenario defaults.
  - Current truth: PR3 keeps `simple_distance` as the default environment routing path for the Gymnasium skeleton.
  - Current truth: real Dundee verification and usefulness-evaluation scripts now exist for the locally built GraphML path.
  - Current truth: if OSMnx is unavailable, the graph is missing, nearest-node snapping fails, or no route exists, runtime can still fall back safely.
  - Still open: whether sampled Dundee success rate, fallback rate, and distance realism are strong enough to justify using OSMnx in later RL evaluation/training loops.

## Dashboard Architecture

- Should the dashboard continue reading `RuntimeStorage` directly or move to FastAPI endpoints?
  - Current truth: dashboard reads storage directly.
  - Pros: simple and local, no API dependency.
  - Cons: dashboard bypasses API contracts and can diverge from mobile/backend behavior, even though runtime status now exposes pricing/routing config fields for visibility.

- Should transformer map markers use topology coordinates?
  - Current truth: `TransformerStateSnapshot` does not include latitude/longitude, while `dashboards/sim_dashboard/app.py` tries to plot transformer dataframe with longitude/latitude.
  - Need verification in a running dashboard.

## Runtime/Data

- How should topology scenario configuration be exposed beyond local/runtime config?
  - Current truth: optional topology scenarios exist in `ev_core.topology.scenarios`.
  - Current truth: `data/processed/topology_scenarios/dundee_synthetic_v1.json` mirrors the processed synthetic layout as a reference scenario.
  - Current truth: `data/processed/topology_scenarios/dundee_synthetic_v1_realistic.json` and `dundee_synthetic_v1_stress.json` provide CP-inventory-calibrated synthetic capacity variants.
  - Current truth: default runtime behavior still uses processed topology unless a scenario is explicitly provided.
  - Current truth: static `capacity_derating_factor` is supported per scenario transformer.
  - Current truth: scenario `capacity_kw` is an active-power modelling approximation, not certified transformer kVA.
  - Still open: API/dashboard controls, scenario catalogs for evaluation, time-varying capacity profiles, and MARL training/evaluation across realistic and stress topology scenarios.

- Is the current transformer/station topology utility-verified?
  - Current truth: no. Processed topology and scenario files are synthetic simulator assumptions only.
  - Risk: interpreting synthetic feeder IDs/capacities as real network data would overstate grid realism.
  - Follow-up: keep utility-verified topology as a separate future data-ingestion task.

- Are the calibrated transformer capacities final?
  - Current truth: no. They are more defensible than the legacy mirrored capacities because they use CP inventory, diversity factors, utilisation margin, and standard capacity steps.
  - Current truth: legacy 150 kW multi-station values remain useful as stress assumptions but should not be described as realistic physical ratings.
  - Still open: utility/DNO data, measured feeder loading, reactive power/kVA modelling, and time-varying operating limits.

- Is `data/processed/background_load_15min.csv` expected to be checked in or generated locally?
  - Current truth: path is referenced by `DundeeDataPaths`, but the file was not present in this workspace.
  - Current truth: repository loading falls back to generated background load when the file is missing.
  - Runtime smoke verification now covers clean-start loading and live recommendations.

- Is `data/processed/station_capacity_assumptions.csv` actually parseable?
  - Current text inspection showed binary/corrupt-looking content.
  - Need pandas read verification in the active environment.

- Should replay fallback use parquet?
  - Current truth: `DundeeDataPaths.model_ready_csv` points to `data/interim/dundee_sessions_model_ready.csv`, but only `.parquet` was observed.

- How far should the runtime go on connector/head realism before MARL work?
  - Current truth: the runtime now uses `chargepoint_master.csv` as a lightweight CP inventory where available.
  - Current truth: each CP row is treated as one usable connector/port for compatibility, available-port counting, best-available power, and internal session assignment.
  - Current truth: queues are still station-level, not per-CP, and public response/snapshot models still do not expose connector assignment.
  - Still open: per-head modelling, per-CP queues, and whether future replay data should bind historical sessions to explicit CP IDs.

## MARL

- What MARL framework/checkpoint format should be used?
  - Current scope: do not add MARL before the single-agent learned-policy path is proven.
  - Intended plug-in architecture is policy-based: offline training -> checkpoint under the agreed artifact path -> checkpoint-backed policy class -> `PolicyRegistry` registration -> `RecommendationService` selection -> deterministic fallback if checkpoint/context/dependencies are missing.
  - First learned models are single-agent MaskablePPO hooks. MARL comes later after the single-agent and feeder paths have stable evaluation, artifact loading, runtime context, and fallback behavior.
  - Still open: final MARL framework/checkpoint format. Likely options remain RLlib, PettingZoo/SuperSuit, CleanRL-style PyTorch modules, Stable-Baselines-style wrappers where applicable, or a custom PyTorch policy.

- What is the observation/action contract for MARL inference?
  - Not verified for MARL.
  - RL/MARL should consume repo-built candidate/runtime features and return rankings or station selections through the recommender policy interface, not change API/mobile contracts.
  - Vehicle profile support has started, but MARL still needs stable candidate features, runtime context, action semantics, charging-curve treatment, and fallback behavior before adding checkpoint inference.

- Should MARL rank all candidates or choose a station directly?
  - Current runtime separates candidate ranking from allocation policy selection during simulation.
  - For the first single-agent MaskablePPO path, use the masked station-selection contract from PR3 and adapt the selected station into the recommender policy path.
  - Need architectural decision before MARL training/inference integration.

- Can offline training happen outside this repo workspace?
  - Yes, on Colab/Kaggle or similar, if it installs and imports this repo code and trains against the repo environment/scenario sampler.
  - Current truth: `ev_core.rl_training` now provides the intended import-safe offline boundary for that workflow.
  - Current truth: selected checkpoint/model artifacts are tracked in Git on this branch.
  - Still open: whether future checkpoints and large run artifacts should stay in normal Git, move to Git LFS, use release assets, or stay in an external artifact store.


## Configuration Rollout

- Shared config contracts now exist in `ev_core.config` with env parsing helpers for runtime/recommendation/routing/pricing/topology/training/deployment.
- Open question: where to incrementally adopt `EVSmartChargingConfig` beyond API runtime bootstrap (for example runtime manager CLI/demo entry points) without behavior drift.
- Open question: when to introduce validation strictness tiers for env parsing in production deployments.
- Open question: exact rollout plan for wiring `RLDeploymentConfig` into `PolicyRegistry` with deterministic fallback guarantees.

## Script Cleanup Follow-Up

- Current truth: `scripts/audit_repo_entrypoints.py` and `docs/ai_context/SCRIPT_AND_FILE_AUDIT.md` now provide a conservative inventory of repo entrypoints and reference evidence.
- Current truth: scripts are now grouped by workflow under `scripts/data`, `scripts/digital_twin`, `scripts/maps`, `scripts/verification`, `scripts/rl_training`, `scripts/forecasting`, and `scripts/benchmarks`.
- Current truth: legacy root-level script names are temporarily kept as compatibility wrappers while docs/tests migrate.
- Current truth: `outputs/test_data` is intentionally retained for now and is not a cleanup target in this PR.
- Open question: when can the compatibility wrappers be removed safely after docs/tests stop using legacy root-level script paths?
- Open question: should some low-reference manual CLIs such as `seed_stations.py`, `verify_app_pricing_duration_alignment.py`, and `verify_runtime_liveness.py` gain explicit docs coverage before any future cleanup discussion?
