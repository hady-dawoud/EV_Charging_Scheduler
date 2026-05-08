# Open Questions

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
  - Current truth: `_distance_simple` uses a simple lat/lon approximation.
  - Current truth: synthetic-live origins are jittered around station/zone anchors, not sampled from road nodes.
  - Need to decide when to introduce routing and which provider/cache to use.

- How should synthetic-live scenarios evolve?
  - Current truth: `SyntheticLiveRequestGenerator` creates valid `ExternalChargingRequest` objects with `source_type="external_live"` and synthetic-live metadata.
  - Current truth: it uses Dundee historical priors, station/zone distributions, and default vehicle profiles without replaying old sessions.
  - Still open: scenario-level demand controls, route-aware origin sampling, richer vehicle-profile priors, and evaluation-set versioning.

## Dashboard Architecture

- Should the dashboard continue reading `RuntimeStorage` directly or move to FastAPI endpoints?
  - Current truth: dashboard reads storage directly.
  - Pros: simple and local, no API dependency.
  - Cons: dashboard bypasses API contracts and can diverge from mobile/backend behavior.

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
  - Not verified. No current MARL checkpoint loading path was found.
  - Need decision among likely options such as RLlib, PettingZoo/SuperSuit, CleanRL-style PyTorch modules, Stable-Baselines-style single-agent wrappers, or a custom PyTorch policy.

- What is the observation/action contract for MARL inference?
  - Not verified.
  - Vehicle profile support has started, but MARL still needs stable candidate features, runtime context, action semantics, charging-curve treatment, and fallback behavior before adding checkpoint inference.

- Should MARL rank all candidates or choose a station directly?
  - Current runtime separates candidate ranking from allocation policy selection during simulation.
  - Need architectural decision before training/inference integration.

