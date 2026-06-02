# Script And File Audit

## Summary

- Scripts scanned: 39
- `api_mobile_integration`: 3
- `dashboard_verification`: 1
- `data_build`: 9
- `digital_twin_runtime`: 6
- `forecasting`: 2
- `general_verification`: 1
- `pricing_verification`: 3
- `rl_training`: 1
- `rl_verification`: 2
- `routing_maps`: 7
- `topology_calibration`: 4
- Scripts with no references: 0
- Scripts recommended to keep: 39
- Scripts needing human review: 0
- Scripts that look safe to delete later: 0

## Scripts With No References

- None

## Scripts Recommended To Keep

- analyze_rl_demand_realism.py
- audit_repo_entrypoints.py
- build_background_load_15min.py
- build_dundee_interactive_maps.py
- build_dundee_osmnx_graph.py
- build_dundee_qc_and_plots.py
- build_dundee_simulator_inputs.py
- build_dundee_spatial_topology.py
- build_dundee_station_catalog.py
- build_optional_pv_tables.py
- build_price_15min.py
- build_request_seed_table.py
- build_station_master.py
- build_transformer_station_map.py
- calibrate_transformer_capacities.py
- clean_acn.py
- clean_dundee.py
- evaluate_osmnx_routing_usefulness.py
- export_osmnx_route_preview.py
- export_sample_contracts.py
- generate_synthetic_live_requests.py
- inject_live_request.py
- run_demo_runtime.py
- seed_stations.py
- smoke_mobile_lifecycle.sh
- verify_app_pricing_duration_alignment.py
- verify_app_runtime_integration.py
- verify_dashboard_smoke.py
- verify_dundee_tariff_pricing.py
- verify_dynamic_pricing.py
- verify_osmnx_routing_provider.py
- verify_rl_env_skeleton.py
- verify_rl_scenario_sampler.py
- verify_routing_provider.py
- verify_runtime_liveness.py
- verify_runtime_smoke.py
- verify_station_access.py
- verify_synthetic_live_requests.py
- verify_topology_scenario.py

## Scripts Needing Human Review

- None

## Scripts That Look Safe To Delete Later

- None

## Proposed Future Script Grouping

- `scripts/data/`
- `scripts/digital_twin/`
- `scripts/maps/`
- `scripts/verification/`
- `scripts/rl_training/`
- `scripts/forecasting/`
- `scripts/benchmarks/`

## Candidate Cleanup Rules

A file can only be deleted if:
1. it is not referenced by docs, tests, or code
2. it is not a useful manual CLI
3. it has been clearly replaced by a newer script
4. full tests pass without it
5. the user approves deletion

## Outputs/Test_Data Policy

- `outputs/test_data` is intentionally kept for now.
- Do not delete it in this PR.
- A later PR may move stable fixtures to `tests/fixtures`.

## Entry Details

### `scripts/analyze_rl_demand_realism.py`

- Category: `rl_training`
- Recommended action: `keep`
- Known manual CLI: `False`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/audit_repo_entrypoints.py`

- Category: `digital_twin_runtime`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=1, python=1, readme_setup=0
- Evidence: Found 5 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/OPEN_QUESTIONS.md, docs/ai_context/REPO_CLEANUP_AND_TRAINING_ARCHITECTURE.md
- tests: tests/architecture/test_script_audit.py
- python: scripts/README.md

### `scripts/build_background_load_15min.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_interactive_maps.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_osmnx_graph.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=1, python=3, readme_setup=0
- Evidence: Found 6 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md
- tests: tests/architecture/test_script_audit.py
- python: scripts/evaluate_osmnx_routing_usefulness.py, scripts/export_osmnx_route_preview.py, scripts/verify_osmnx_routing_provider.py

### `scripts/build_dundee_qc_and_plots.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_simulator_inputs.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_spatial_topology.py`

- Category: `topology_calibration`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_station_catalog.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_optional_pv_tables.py`

- Category: `forecasting`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_price_15min.py`

- Category: `forecasting`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_request_seed_table.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_station_master.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_transformer_station_map.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/calibrate_transformer_capacities.py`

- Category: `topology_calibration`
- Recommended action: `keep`
- Known manual CLI: `False`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md

### `scripts/clean_acn.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/clean_dundee.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/evaluate_osmnx_routing_usefulness.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/export_osmnx_route_preview.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/export_sample_contracts.py`

- Category: `api_mobile_integration`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/generate_synthetic_live_requests.py`

- Category: `digital_twin_runtime`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md, docs/ai_context/REQUEST_FLOW.md

### `scripts/inject_live_request.py`

- Category: `digital_twin_runtime`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=2
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- readme_setup: README.md, REPO_STRUCTURE.md

### `scripts/run_demo_runtime.py`

- Category: `digital_twin_runtime`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=2
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- readme_setup: README.md, REPO_STRUCTURE.md

### `scripts/seed_stations.py`

- Category: `data_build`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md

### `scripts/smoke_mobile_lifecycle.sh`

- Category: `api_mobile_integration`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=1, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- tests: tests/architecture/test_script_audit.py

### `scripts/verify_app_pricing_duration_alignment.py`

- Category: `pricing_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md

### `scripts/verify_app_runtime_integration.py`

- Category: `api_mobile_integration`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_dashboard_smoke.py`

- Category: `dashboard_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=1, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- tests: tests/architecture/test_script_audit.py

### `scripts/verify_dundee_tariff_pricing.py`

- Category: `pricing_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_dynamic_pricing.py`

- Category: `pricing_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_osmnx_routing_provider.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/verify_rl_env_skeleton.py`

- Category: `rl_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=1, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- tests: tests/architecture/test_script_audit.py

### `scripts/verify_rl_scenario_sampler.py`

- Category: `rl_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md

### `scripts/verify_routing_provider.py`

- Category: `routing_maps`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/verify_runtime_liveness.py`

- Category: `digital_twin_runtime`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md

### `scripts/verify_runtime_smoke.py`

- Category: `digital_twin_runtime`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=1, python=0, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md
- tests: tests/architecture/test_script_audit.py

### `scripts/verify_station_access.py`

- Category: `topology_calibration`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/verify_synthetic_live_requests.py`

- Category: `general_verification`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/REQUEST_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_topology_scenario.py`

- Category: `topology_calibration`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md

## Known Warning

- No unreadable `outputs/runtime` path was encountered during this audit run.

