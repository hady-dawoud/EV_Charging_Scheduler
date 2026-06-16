# RL Training Scripts

This folder holds RL scenario, environment, and demand-analysis entrypoints tied to offline training preparation.

Use these scripts for RL-specific verification and future training/evaluation helpers.

Current verification entrypoints:
- `verify_rl_env_skeleton.py`: checks the base masked `ev_core.rl.env` skeleton.
- `verify_offline_rl_training_env.py`: checks the offline `ev_core.rl_training` wrapper/factory/rollout boundary that reuses the existing env.
- `train_maskable_ppo_station_selector.py`: dry-run/train entrypoint for the older Dundee station-selection MaskablePPO path.
- `train_maskable_ppo_feeder_station_selector.py`: dry-run/train entrypoint for the DigitalTwin feeder public-EV MaskablePPO path.
- `evaluate_maskable_ppo_feeder_station_selector.py`: feeder checkpoint evaluation entrypoint.

Design notes:
- `simple_distance` remains the default routing provider.
- The offline wrapper is separate from the app-facing runtime/digital twin.
- SB3, `sb3-contrib`, Torch, TensorBoard, and Gymnasium remain optional dependencies for full training/evaluation. Dry-run paths report dependency availability without starting training.
- Feeder training/evaluation still requires the feeder RL data package, which is not present in this repo checkout.
