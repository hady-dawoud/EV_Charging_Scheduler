# RL Training Scripts

This folder holds RL scenario, environment, and demand-analysis entrypoints tied to offline training preparation.

Use these scripts for RL-specific verification and future training/evaluation helpers.

Current verification entrypoints:
- `verify_rl_env_skeleton.py`: checks the base masked `ev_core.rl.env` skeleton.
- `verify_offline_rl_training_env.py`: checks the offline `ev_core.rl_training` wrapper/factory/rollout boundary that reuses the existing env.

Design notes:
- `simple_distance` remains the default routing provider.
- The offline wrapper is separate from the app-facing runtime/digital twin.
- No SB3, `sb3-contrib`, or MaskablePPO training is added here yet.
