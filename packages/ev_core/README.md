# ev_core

Standalone Python scaffolding for the EV-side data, preprocessing, forecasting,
simulation, and recommendation layers.

## Why this exists

This package is intentionally separate from the current mocked backend and
mobile app workflow in `apps/api` and `apps/mobile`.

- It does not change or extend the running FastAPI routes.
- It does not change or extend the current Expo/React Native screens.
- It is not wired into the app flow yet.

## Intended package layout

- `contracts`: shared schemas and type aliases for future backend, simulation,
  and recommendation integration.
- `data`: input/output helpers, preprocessing entry points, and repository
  abstractions.
- `env`: request-driven multi-agent simulation scaffolding built around a
  15-minute internal time base.
- `forecasting`: provider interfaces and dummy implementations for background
  load, price, and optional PV forecasts.
- `recommender`: future ranking and service layer placeholders.
- `utils`: small shared helpers such as logging and time-base utilities.

## Current scope

Only safe placeholders, typed models, and TODO-friendly stubs are included
here. No production logic has been implemented yet.
