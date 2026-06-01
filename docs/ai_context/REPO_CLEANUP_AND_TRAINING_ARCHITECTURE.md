# Repo Cleanup and Training Architecture

## Objective

Introduce explicit architecture boundaries so offline training can evolve without coupling to app/runtime surfaces.

## Boundary model

- `ev_core.digital_twin` stays app-facing and runtime-oriented.
- `ev_core.rl_training` is the offline training boundary.
- `ev_core.benchmarks` hosts optional benchmark adapters.
- `ev_core.deployment` hosts checkpoint inference/deployment contracts.

## Runtime and app-facing scope

Current app-facing flows remain where they are today (`apps/api`, `apps/mobile`, `dashboards/sim_dashboard`, and `services/sim_runtime`).
Digital twin/runtime behavior remains the source of live recommendation behavior.

## Offline training scope

`ev_core.rl_training` is reserved for offline RL training concerns only. It must not import or require:
- FastAPI
- Streamlit
- `apps/*`
- dashboard modules
- `services.sim_runtime.storage`

This keeps training code reusable and testable in non-app contexts.

## Benchmark adapters

EV2Gym and SustainGym are future adapter targets under `ev_core.benchmarks`; they are not the main app runtime. Core imports must remain functional without benchmark packages installed.

## Deployment and policy integration

Trained checkpoints are expected to plug in through deployment-time inference code and later `PolicyRegistry` integration. This separation avoids mixing training-time dependencies into runtime services.

## Cleanup policy for this phase

- Script cleanup is deferred until audit-backed follow-up PRs.
- `outputs/test_data` is intentionally kept as-is for now.
- No runtime/API/mobile/dashboard response shape changes are made in this phase.

## Follow-up PRs

Planned follow-ups after this boundary PR:
- Configuration surfaces for training/deployment paths.
- Script inventory and audit-based cleanup.
- Offline environment evolution.
- MaskablePPO exploration (deferred by design in this PR).
- Forecasting integration for training features.
- Benchmark adapters.
- Deployment/checkpoint loading and inference wiring.

## PR2 Shared Configuration Boundaries

This PR adds a shared, dependency-light config package at `ev_core.config`.

Added contracts:
- `ProjectPathsConfig`
- `DigitalTwinRuntimeConfig`
- `RecommendationConfig`
- `RoutingConfig`
- `PricingConfig`
- `TopologyConfig`
- `RLTrainingConfig`
- `ForecastTrainingConfig`
- `RLDeploymentConfig`
- aggregate `EVSmartChargingConfig`

Key constraints preserved:
- `simple_distance` remains the default routing provider.
- OSMnx remains optional and non-default.
- No MaskablePPO, no MARL, and no training/inference runtime wiring in this PR.
- No API/mobile/dashboard response-shape changes.
- No changes to pricing formulas, routing behavior, or ranking behavior.
