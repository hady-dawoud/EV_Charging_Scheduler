# Simulator Dashboard

This Streamlit dashboard visualizes the standalone Dundee simulator runtime outside `apps/**`.

It reads only the shared runtime artifacts under `outputs/runtime/` plus the persisted SQLite history written by `services/sim_runtime/`.

The dashboard is intentionally independent from the existing API/mobile prototype layers so future integration can happen through contracts and runtime storage rather than by coupling to `apps/**`.
