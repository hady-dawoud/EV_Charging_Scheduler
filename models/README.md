# Models Directory

This branch currently tracks the selected runtime model artifacts in Git.

Current tracked artifacts:

```text
models/
  rl/
    maskable_ppo_station_selector.zip
  rl_feeder/
    maskable_ppo_feeder_station_selector.zip
  rl_feeder_final/
    maskable_ppo_feeder_station_selector.zip
  forecasting/
    load_kw_30min/
      lstm_huber_load_kw_30min.keras
      load_kw_30min_feature_scaler.joblib
      load_kw_30min_target_scaler.joblib
      load_kw_30min_training_metadata.json
```

Important notes:

- `.gitattributes` currently configures Git LFS only for `data/interim/*.csv`; these model files are normal Git-tracked files.
- Future PRs should decide whether to keep model binaries in Git, move them to Git LFS, or publish them as release/external artifacts.
- Do not unzip checkpoint archives into the repo.
