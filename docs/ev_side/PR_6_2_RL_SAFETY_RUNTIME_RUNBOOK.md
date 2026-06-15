# PR 6.2 RL Safety Runtime Runbook

## Scope And Evidence Boundary

PR 6.2 adds an optional feeder RL safety layer around the existing app
preference rankers:

```text
app candidate construction with dynamic pricing
-> optional feeder runtime context and checkpoint prediction
-> exact or explicitly nonphysical demo mapping
-> bounded safety penalty or blocking
-> existing deterministic preference ranker adjusted by safety
-> unchanged response schema
```

The repository default remains deterministic `weighted_score`. Hybrid policies
must be selected explicitly or enabled through `RL_SAFETY_FILTER_ENABLED`.
Torch, Stable-Baselines3, and sb3-contrib remain optional until checkpoint
inference is enabled.

The checkpoint is not preference-conditioned and is advisory only. `closest`
still starts from distance, `cheapest` still starts from dynamic
`estimated_cost_gbp`, `fastest` still starts from duration/wait, and
`weighted_score` keeps its existing formula. Forecast metadata is not fed into
the checkpoint.

Feeder-evaluator metrics remain the primary grid-performance evidence.
App/runtime verification is secondary service/demo context. App recommendation
success rate is not a feeder grid-performance metric. PR 6.1 remains paused
feeder-evaluator evidence infrastructure; the hybrid evidence benchmark belongs
to future PR 6.3.

## Current Machine Safety

As of June 15, 2026, the active development workspace on this machine is:

```text
D:\Omar\ev-smart-charging
```

Repository folders under `G:\OMAR\Graduation Project`,
`G:\OMAR\Graduation Project Safe Clone`, and `G:\OMAR\GRAD` are historical
corruption/recovery evidence only. Do not use them for development, Git
operations, dependency resolution, or runtime artifact discovery.

## Required Deployment Artifacts

The checkpoint is expected at:

```text
models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip
```

Strict verification and feeder runtime context require these local files:

```text
data/processed/evside_feeder_rl/manifest.json
data/processed/evside_feeder_rl/feature_stats.json
data/processed/evside_feeder_rl/feeder_ev_action_catalog.parquet
data/processed/evside_feeder_rl/feeder_request_priors.parquet
data/processed/evside_feeder_rl/feeder_grid_advisory_replay.parquet
```

`manifest.json` and `feature_stats.json` are tracked as normal Git text files.
The three parquet files and the strict checkpoint are tracked with Git LFS.
After cloning, materialize them before starting strict mode:

```powershell
git lfs install
git lfs pull
python scripts\verification\check_deployment_artifacts.py --json
uv run --with pandas --with pyarrow python scripts\verification\check_deployment_artifacts.py --json --check-parquet
```

The Docker services mount `data/` and `models/rl_feeder_final/` read-only.
Never replace missing artifacts with fabricated data to make strict
verification pass.

## Configuration

Use `.env.feeder_rl_demo.example` as the secret-free strict template. The
recommended physical mode is `exact_only`, where unmatched candidates remain
unmapped and unpenalized with diagnostics.

`stable_ordinal_demo_bridge` deterministically pairs sorted app candidate IDs
with sorted valid feeder station/action pairs. It is always labeled:

```text
rl_safety_mapping_kind=stable_ordinal_demo_bridge
rl_safety_mapping_physical_claim=false
offline_feeder_rl_adapter=true
rl_safety_mapping_warning=nonphysical_demo_mapping
```

This bridge is app/demo-only and cannot support claims about physical station
identity or primary grid performance.

Penalty mode computes:

```text
adjusted_score = base_preference_score
                 - penalty_weight * safety_penalty
```

Both penalty values are bounded to `[0.0, 1.0]`; higher adjusted score remains
better. Raw user-facing fields and dynamic-pricing metadata are unchanged.
Block mode removes eligible unsafe candidates only when configured. All-blocked
fail-open restores deterministic ranking with diagnostics; fail-closed returns
the controlled empty/error behavior.

## Verification

Run the focused helper tests:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\verification\test_rl_safety_preference_ranking.py -q
```

Run dependency-light verification:

```powershell
uv run --with pydantic --with numpy --with pandas python scripts\verification\verify_rl_safety_preference_ranking.py
```

Run strict checkpoint verification:

```powershell
uv run --with pyarrow --with pydantic --with numpy --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\verify_rl_safety_preference_ranking.py --strict
```

Strict success requires materialized Git LFS objects, checkpoint availability,
a 2200-feature observation,
the expected action mask/catalog alignment, and `fallback_used=false`.

Run the Phase E/PR 6.2 regression:

```powershell
uv run --with pytest --with pydantic --with numpy pytest tests\recommender\test_rl_safety_filter.py tests\recommender\test_rl_safety_policies.py tests\recommender\test_policy_registry.py tests\recommender\test_dundee_env_recommendation_policy.py tests\recommender\test_recommendation_service.py tests\api\test_runtime_service_recommendation_policy_config.py tests\sim_runtime\test_runtime_recommendation_policy.py -q
```

The existing end-to-end simulator/API commands remain in the root `README.md`.
Loading the feeder demo environment is an explicit opt-in; those commands keep
their deterministic behavior otherwise.

## Local Docker Deployment

The compose stack uses `postgres` for container-to-container database access.
The mobile web build defaults to `http://localhost:8000`, while the dashboard
shares `outputs/runtime/` with the runtime and API containers.

```powershell
Copy-Item .env.example .env
git lfs pull
python scripts\verification\check_deployment_artifacts.py
docker compose config
docker compose up --build
```

Local endpoints:

```text
mobile web: http://localhost:3000
API:        http://localhost:8000
dashboard:  http://localhost:8501
```

Override `EXPO_PUBLIC_API_BASE_URL` and `VITE_API_BASE_URL` before building
when the browser reaches the API through another host or reverse proxy.

## Repository Health

Before trusting a workspace:

```powershell
git fsck --full
python scripts\verification\audit_tracked_text_files.py
git diff --check
```

The tracked-source audit fails on null bytes, invalid UTF-8, or Python syntax
errors. It intentionally ignores generated data trees, untracked runtime
artifacts, generated output, caches, and binary model files. Validate data
artifacts separately with their JSON/Parquet/CSV readers.

## Last Known Phase E Result

On June 15, 2026, strict verification passed in the active D: workspace with a
2200-feature observation, 73 catalog actions, 21 valid actions, checkpoint
action metadata present, and no fallback. Re-run the commands above after any
source, checkpoint, dependency, or replay-artifact change.
