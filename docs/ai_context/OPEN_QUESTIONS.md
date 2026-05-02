# Open Questions

## Request Contract

- Is `request_timestamp` required for mobile/live requests?
  - Current truth: `ExternalChargingRequest.request_timestamp` is required.
  - Risk: mobile can provide it, but API clients without a client-side timestamp will fail validation.
  - Need to decide whether backend should default missing timestamps to server time.

- How should `requested_energy_kwh` mismatch with SOC-derived energy be handled?
  - Current truth: if `requested_energy_kwh` is supplied, the model keeps it and does not compare it to `target_soc`, `current_soc`, and `battery_kwh`.
  - Risk: mobile sends both explicit energy and SOC fields.
  - Need policy: trust explicit energy, reject mismatch, warn in metadata, or recompute.

- What domain validation should be enforced first?
  - Not yet strongly enforced: SOC range, battery capacity > 0, energy > 0, latest finish after request timestamp, coordinate bounds, plausible Dundee location, max request window.

## Candidate Eligibility

- Should Greenmarket bus charger, car-club, depot, or other restricted/special-purpose stations be public recommendation candidates?
  - Current truth: candidate builder loops over all stations in `station_index`.
  - Any station present in `station_master` and compatible by connector/window can be recommended.
  - Need business/domain rule for public eligibility flags.

- Should distance be road routing or simple approximation?
  - Current truth: `_distance_simple` uses a simple lat/lon approximation.
  - Need to decide when to introduce routing and which provider/cache to use.

## Dashboard Architecture

- Should the dashboard continue reading `RuntimeStorage` directly or move to FastAPI endpoints?
  - Current truth: dashboard reads storage directly.
  - Pros: simple and local, no API dependency.
  - Cons: dashboard bypasses API contracts and can diverge from mobile/backend behavior.

- Should transformer map markers use topology coordinates?
  - Current truth: `TransformerStateSnapshot` does not include latitude/longitude, while `dashboards/sim_dashboard/app.py` tries to plot transformer dataframe with longitude/latitude.
  - Need verification in a running dashboard.

## Runtime/Data

- Is `data/processed/background_load_15min.csv` expected to be checked in or generated locally?
  - Current truth: path is referenced by `DundeeDataPaths`, but the file was not present in this workspace.
  - Need clean-start runtime verification.

- Is `data/processed/station_capacity_assumptions.csv` actually parseable?
  - Current text inspection showed binary/corrupt-looking content.
  - Need pandas read verification in the active environment.

- Should replay fallback use parquet?
  - Current truth: `DundeeDataPaths.model_ready_csv` points to `data/interim/dundee_sessions_model_ready.csv`, but only `.parquet` was observed.

## MARL

- What MARL framework/checkpoint format should be used?
  - Not verified. No current MARL checkpoint loading path was found.
  - Need decision among likely options such as RLlib, PettingZoo/SuperSuit, CleanRL-style PyTorch modules, Stable-Baselines-style single-agent wrappers, or a custom PyTorch policy.

- What is the observation/action contract for MARL inference?
  - Not verified.
  - Need stable candidate features, runtime context, action semantics, and fallback behavior before adding checkpoint inference.

- Should MARL rank all candidates or choose a station directly?
  - Current runtime separates candidate ranking from allocation policy selection during simulation.
  - Need architectural decision before training/inference integration.

