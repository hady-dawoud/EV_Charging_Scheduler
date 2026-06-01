# ev_core.rl_training

This package is reserved for offline RL training pipelines and utilities.

Design constraints:
- Must remain independent from FastAPI, Streamlit, `apps/*`, and dashboard code.
- Must not depend on runtime storage internals from `services/sim_runtime`.
- Should expose composable, configurable training interfaces for future policy work.

Current status:
- Boundary scaffolding only.
- Existing behavior remains in current runtime/recommender code paths.
