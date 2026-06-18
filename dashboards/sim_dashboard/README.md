# Simulator Dashboard

This Streamlit dashboard visualizes the standalone Dundee simulator runtime outside `apps/**`.

It reads only the shared runtime artifacts under `outputs/runtime/` plus the persisted SQLite history written by `services/sim_runtime/`.

The dashboard is intentionally independent from the existing API/mobile prototype layers so future integration can happen through contracts and runtime storage rather than by coupling to `apps/**`.

## Run

From the repository root, run the dashboard using the existing API virtual environment:

```bash
./apps/api/.venv/Scripts/python.exe -m streamlit run dashboards/sim_dashboard/app.py --server.headless true --server.port 8501
```

Open locally:

```text
http://127.0.0.1:8501
```

The VM dashboard test URL is:

```text
https://smartevcharging.uaenorth.cloudapp.azure.com/dashboard/
```

## Data loading

The dashboard reads `RuntimeStorage` first:

- `get_recent_external_requests()`
- `get_recent_recommendations()`

If either SQLite-backed call returns no records, the dashboard falls back to the existing JSON artifacts under `outputs/runtime/` and validates them with the existing Pydantic runtime contracts:

- `ExternalChargingRequest`
- `RecommendationResponse`

## Deployment compatibility

`Dockerfile.dashboard` and `docker-compose.yml` are intentionally unchanged for dashboard UI/data-display work unless a concrete build or runtime test proves they need a change.
