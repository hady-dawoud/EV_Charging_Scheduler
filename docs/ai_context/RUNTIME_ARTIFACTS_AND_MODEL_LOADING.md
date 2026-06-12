# Runtime Artifacts And Model Loading

Last verified against repo state: 2026-06-13 on branch `MARL`.

This document summarizes the repo-local runtime artifacts needed for optional RL, feeder RL, and forecasting paths. It is intentionally about artifact presence and loading boundaries, not training quality.

## Current Summary

Present in this checkout:

- `models/rl/maskable_ppo_station_selector.zip`
- `models/rl_feeder/maskable_ppo_feeder_station_selector.zip`
- `models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip`
- `models/forecasting/load_kw_30min/lstm_huber_load_kw_30min.keras`
- `models/forecasting/load_kw_30min/load_kw_30min_feature_scaler.joblib`
- `models/forecasting/load_kw_30min/load_kw_30min_target_scaler.joblib`
- `models/forecasting/load_kw_30min/load_kw_30min_training_metadata.json`

Missing in this checkout:

- `data/processed/evside_feeder_rl/manifest.json`
- `data/processed/evside_feeder_rl/feature_stats.json`
- `data/processed/evside_feeder_rl/feeder_ev_action_catalog.csv` or `.parquet`
- `data/processed/evside_feeder_rl/feeder_request_priors.csv` or `.parquet`
- `data/processed/evside_feeder_rl/feeder_grid_advisory_replay.csv` or `.parquet`

Storage policy truth:

- The model artifacts above are currently tracked by normal Git, not Git LFS.
- `.gitattributes` currently only marks `data/interim/*.csv` for Git LFS.
- `archive/` is ignored by Git and should be treated as local scratch/staging for external snapshots.

## RL Checkpoint Paths

Older Dundee station-selection policy:

```text
models/rl/maskable_ppo_station_selector.zip
```

Runtime policy hook:

```text
packages/ev_core/src/ev_core/recommender/rl_policy.py
```

Policy name:

```text
rl_maskable_ppo
```

Relevant environment variables:

```text
RECOMMENDATION_POLICY_NAME=rl_maskable_ppo
RL_POLICY_CHECKPOINT_PATH=models/rl/maskable_ppo_station_selector.zip
RL_POLICY_FAIL_CLOSED=false
GRID_ADVISORY_MODE=disabled|recorded|http|runtime_http
GRID_ADVISORY_REPLAY_DIR=data/processed/evside_feeder_rl
```

Fallback behavior:

- Missing checkpoint: fallback to `weighted_score` unless fail-closed is enabled.
- Missing `sb3_contrib`: fallback.
- Missing simulation request/station context: fallback.
- Invalid prediction or empty action mask: fallback.

## Feeder RL Checkpoint Paths

Feeder training checkpoint:

```text
models/rl_feeder/maskable_ppo_feeder_station_selector.zip
```

Final evaluated feeder checkpoint:

```text
models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip
```

Runtime policy hook:

```text
packages/ev_core/src/ev_core/recommender/feeder_rl_policy.py
```

Policy name:

```text
rl_maskable_ppo_feeder
```

Relevant environment variables:

```text
RECOMMENDATION_POLICY_NAME=rl_maskable_ppo_feeder
RL_FEEDER_CHECKPOINT_PATH=models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip
```

Runtime context required by the feeder policy:

- `feeder_observation`
- `feeder_action_mask`
- `feeder_station_ids`
- optional `grid_advisories`

Fallback behavior:

- Missing checkpoint: fallback to `weighted_score`.
- Missing `sb3_contrib`: fallback.
- Missing feeder runtime context: fallback.
- Invalid prediction or empty action mask: fallback.

## Feeder RL Data Package

Proposed repo-local canonical path:

```text
data/processed/evside_feeder_rl/
```

Required package:

```text
data/processed/evside_feeder_rl/manifest.json
data/processed/evside_feeder_rl/feature_stats.json
data/processed/evside_feeder_rl/feeder_ev_action_catalog.csv
data/processed/evside_feeder_rl/feeder_request_priors.csv
data/processed/evside_feeder_rl/feeder_grid_advisory_replay.csv
```

Parquet alternatives are accepted for the three tabular files.

What uses it:

- `DigitalTwinFeederRLRepository`
- `FeederObservationBuilder`
- `FeederStationSelectionEnv`
- recorded grid advisory replay lookup
- feeder training/evaluation scripts

Current blocker:

- This data package is absent. The feeder checkpoint can be present while still being unusable for true feeder inference because observations and action masks cannot be rebuilt.

## Forecast Model Paths

Selected model:

```text
models/forecasting/load_kw_30min/lstm_huber_load_kw_30min.keras
```

Required scalers/metadata:

```text
models/forecasting/load_kw_30min/load_kw_30min_feature_scaler.joblib
models/forecasting/load_kw_30min/load_kw_30min_target_scaler.joblib
models/forecasting/load_kw_30min/load_kw_30min_training_metadata.json
```

Metadata summary:

- target: `load_kw_30min`
- frequency: `30min`
- lookback: `48`
- feature count: `148`
- input shape: `[48, 148]`
- target shape: `[1]`
- TensorFlow version from training metadata: `2.18.0`

Current runtime status:

- `ForecastProvider` is present as an interface.
- `NullForecastProvider` and table-backed `PlaceholderForecastProvider` are implemented.
- No model-backed provider currently loads this Keras model.
- Forecasting must not change the pretrained RL observation shape unless a checkpoint is retrained for that shape.

## Smoke Checks

Current artifact audit:

```powershell
python scripts/audit_runtime_artifacts.py
```

Strict CI-style audit:

```powershell
python scripts/audit_runtime_artifacts.py --strict
```

Expected current result:

- default audit exits `0`
- strict audit exits `1` until the feeder RL data package exists

After feeder data is added, smoke-check the package without training:

```powershell
python scripts/rl_training/train_maskable_ppo_feeder_station_selector.py --feeder-rl-data-dir data/processed/evside_feeder_rl --dry-run
```

After feeder dependencies and data are available, evaluate a checkpoint:

```powershell
python scripts/rl_training/evaluate_maskable_ppo_feeder_station_selector.py --feeder-rl-data-dir data/processed/evside_feeder_rl --checkpoint-path models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip --grid-advisory-mode recorded
```

After forecasting integration exists, the first safe smoke check should load the model and expose forecast output without changing recommendation rankings or response contracts. A later forecast-aware ranking change should be tested separately from checkpoint loading.
