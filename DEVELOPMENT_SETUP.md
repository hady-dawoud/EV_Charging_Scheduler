# Development Setup

This repo now includes additive scaffolding for EV-side data work,
preprocessing, forecasting, simulation, and recommendation research.

## Important separation

- The current mocked application flow remains under `apps/api` and
  `apps/mobile`.
- The new scaffolding lives under `packages/ev_core`, `data/`, `scripts/`,
  `config/`, `notebooks/`, and `outputs/`.
- Nothing in the new scaffolding is wired into the running API or mobile app
  yet.

## Virtual environments

- `apps/api/.venv` remains the local environment for the FastAPI app.
- `./.venv` at the repo root is intended for the new EV-core scaffolding,
  notebooks, and data scripts.

## Suggested root setup

```powershell
uv venv .venv
.venv\Scripts\python.exe -m pip install -e .\packages\ev_core
```

## Notes

- Use the `scripts/` folder as future CLI entry points for preprocessing and
  table generation.
- Use the `config/` folder for simulation defaults and source registry files.
- Use the `notebooks/` folder for exploratory analysis and environment design.
- Use a 15-minute internal time base for derived tables and simulation-oriented
  artifacts unless a later design note explicitly changes it.
