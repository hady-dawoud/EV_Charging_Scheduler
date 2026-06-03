# ev_core.rl_training

This package is reserved for offline RL training pipelines and utilities.

Design constraints:
- Must remain independent from FastAPI, Streamlit, `apps/*`, and dashboard code.
- Must not depend on runtime storage internals from `services/sim_runtime`.
- Should expose composable, configurable training interfaces for future policy work.
- May wrap `ev_core.rl.env.DundeeStationSelectionEnv`, but should not fork its action-mask, observation, or reward logic in the first offline-training pass.

Current status:
- `offline_station_selection_env.py` exposes the training-facing wrapper around `DundeeStationSelectionEnv`.
- `scenario_factory.py` creates reproducible Dundee train/validation/test scenarios from `RLScenarioSampler` and `RLTrainingConfig`.
- `data_adapter.py` loads Dundee bundle counts, request-generation inputs, and scenario samplers without runtime storage coupling.
- `rollout.py` runs random-valid, fixed-action, and deterministic recommendation-policy rollouts without SB3.
- `metrics.py` summarizes rollout outputs into lightweight aggregate metrics.

Still intentionally deferred:
- MaskablePPO / `sb3-contrib`
- Stable-Baselines3
- MARL
- EV2Gym / SustainGym adapters
- checkpoint loading or runtime `PolicyRegistry` integration
