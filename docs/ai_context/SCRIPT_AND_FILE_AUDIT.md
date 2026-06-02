# Script And File Audit

## Summary

- Scripts scanned: 77
- `api_mobile_integration`: 6
- `dashboard_verification`: 2
- `data_build`: 18
- `digital_twin_runtime`: 11
- `forecasting`: 4
- `general_verification`: 2
- `pricing_verification`: 6
- `rl_training`: 2
- `rl_verification`: 4
- `routing_maps`: 14
- `topology_calibration`: 8
- Grouped implementation scripts: 38
- Legacy compatibility wrappers: 38
- Scripts with no references: 0
- Scripts recommended to keep: 77
- Scripts needing human review: 0
- Scripts that look safe to delete later: 0

## Grouped Script Folders

- `scripts/data/`
- `scripts/digital_twin/`
- `scripts/maps/`
- `scripts/verification/`
- `scripts/rl_training/`
- `scripts/forecasting/`
- `scripts/benchmarks/`

## Compatibility Wrappers

- Legacy root-level script paths are kept as thin wrappers in this PR.
- Wrappers are temporary compatibility entrypoints and should be removed only after docs and tests migrate.

## Scripts With No References

- None

## Scripts Recommended To Keep

- analyze_rl_demand_realism.py
- analyze_rl_demand_realism.py
- audit_repo_entrypoints.py
- build_background_load_15min.py
- build_background_load_15min.py
- build_dundee_interactive_maps.py
- build_dundee_interactive_maps.py
- build_dundee_osmnx_graph.py
- build_dundee_osmnx_graph.py
- build_dundee_qc_and_plots.py
- build_dundee_qc_and_plots.py
- build_dundee_simulator_inputs.py
- build_dundee_simulator_inputs.py
- build_dundee_spatial_topology.py
- build_dundee_spatial_topology.py
- build_dundee_station_catalog.py
- build_dundee_station_catalog.py
- build_optional_pv_tables.py
- build_optional_pv_tables.py
- build_price_15min.py
- build_price_15min.py
- build_request_seed_table.py
- build_request_seed_table.py
- build_station_master.py
- build_station_master.py
- build_transformer_station_map.py
- build_transformer_station_map.py
- calibrate_transformer_capacities.py
- calibrate_transformer_capacities.py
- clean_acn.py
- clean_acn.py
- clean_dundee.py
- clean_dundee.py
- evaluate_osmnx_routing_usefulness.py
- evaluate_osmnx_routing_usefulness.py
- export_osmnx_route_preview.py
- export_osmnx_route_preview.py
- export_sample_contracts.py
- export_sample_contracts.py
- generate_synthetic_live_requests.py
- generate_synthetic_live_requests.py
- inject_live_request.py
- inject_live_request.py
- run_demo_runtime.py
- run_demo_runtime.py
- seed_stations.py
- seed_stations.py
- smoke_mobile_lifecycle.sh
- smoke_mobile_lifecycle.sh
- verify_app_pricing_duration_alignment.py
- verify_app_pricing_duration_alignment.py
- verify_app_runtime_integration.py
- verify_app_runtime_integration.py
- verify_dashboard_smoke.py
- verify_dashboard_smoke.py
- verify_dundee_tariff_pricing.py
- verify_dundee_tariff_pricing.py
- verify_dynamic_pricing.py
- verify_dynamic_pricing.py
- verify_osmnx_routing_provider.py
- verify_osmnx_routing_provider.py
- verify_rl_env_skeleton.py
- verify_rl_env_skeleton.py
- verify_rl_scenario_sampler.py
- verify_rl_scenario_sampler.py
- verify_routing_provider.py
- verify_routing_provider.py
- verify_runtime_liveness.py
- verify_runtime_liveness.py
- verify_runtime_smoke.py
- verify_runtime_smoke.py
- verify_station_access.py
- verify_station_access.py
- verify_synthetic_live_requests.py
- verify_synthetic_live_requests.py
- verify_topology_scenario.py
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
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `False`
- Wrapper target: `scripts/rl_training/analyze_rl_demand_realism.py`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/audit_repo_entrypoints.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `root_entrypoint`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=2, python=1, readme_setup=0
- Evidence: Found 6 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/OPEN_QUESTIONS.md, docs/ai_context/REPO_CLEANUP_AND_TRAINING_ARCHITECTURE.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py
- python: scripts/README.md

### `scripts/build_background_load_15min.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_background_load_15min.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_interactive_maps.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/maps/build_dundee_interactive_maps.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_osmnx_graph.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/maps/build_dundee_osmnx_graph.py`
- Reference counts: ai_context=2, docs=0, tests=2, python=3, readme_setup=0
- Evidence: Found 7 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py
- python: scripts/maps/evaluate_osmnx_routing_usefulness.py, scripts/maps/export_osmnx_route_preview.py, scripts/maps/verify_osmnx_routing_provider.py

### `scripts/build_dundee_qc_and_plots.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_dundee_qc_and_plots.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_simulator_inputs.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_dundee_simulator_inputs.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_spatial_topology.py`

- Category: `topology_calibration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_dundee_spatial_topology.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_dundee_station_catalog.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_dundee_station_catalog.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_optional_pv_tables.py`

- Category: `forecasting`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/forecasting/build_optional_pv_tables.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_price_15min.py`

- Category: `forecasting`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/forecasting/build_price_15min.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_request_seed_table.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_request_seed_table.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_station_master.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_station_master.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/build_transformer_station_map.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/build_transformer_station_map.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/calibrate_transformer_capacities.py`

- Category: `topology_calibration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `False`
- Wrapper target: `scripts/data/calibrate_transformer_capacities.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md

### `scripts/clean_acn.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/clean_acn.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/clean_dundee.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/clean_dundee.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_background_load_15min.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_background_load_15min.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_dundee_qc_and_plots.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_dundee_qc_and_plots.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_dundee_simulator_inputs.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_dundee_simulator_inputs.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_dundee_spatial_topology.py`

- Category: `topology_calibration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_dundee_spatial_topology.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_dundee_station_catalog.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_dundee_station_catalog.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_request_seed_table.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_request_seed_table.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_station_master.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_station_master.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/build_transformer_station_map.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_transformer_station_map.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/calibrate_transformer_capacities.py`

- Category: `topology_calibration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `False`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- python: scripts/calibrate_transformer_capacities.py

### `scripts/data/clean_acn.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/clean_acn.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/clean_dundee.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/clean_dundee.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/data/seed_stations.py`

- Category: `data_build`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md
- python: scripts/seed_stations.py

### `scripts/digital_twin/export_sample_contracts.py`

- Category: `api_mobile_integration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/export_sample_contracts.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/digital_twin/generate_synthetic_live_requests.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md, docs/ai_context/REQUEST_FLOW.md
- python: scripts/generate_synthetic_live_requests.py

### `scripts/digital_twin/inject_live_request.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=2
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- python: scripts/inject_live_request.py
- readme_setup: README.md, REPO_STRUCTURE.md

### `scripts/digital_twin/run_demo_runtime.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=2
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- python: scripts/run_demo_runtime.py
- readme_setup: README.md, REPO_STRUCTURE.md

### `scripts/digital_twin/verify_app_runtime_integration.py`

- Category: `api_mobile_integration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RL_READINESS_REPORT.md
- python: scripts/verify_app_runtime_integration.py

### `scripts/digital_twin/verify_runtime_liveness.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md
- python: scripts/verify_runtime_liveness.py

### `scripts/digital_twin/verify_runtime_smoke.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=2, python=1, readme_setup=0
- Evidence: Found 6 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py
- python: scripts/verify_runtime_smoke.py

### `scripts/evaluate_osmnx_routing_usefulness.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/maps/evaluate_osmnx_routing_usefulness.py`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/export_osmnx_route_preview.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/maps/export_osmnx_route_preview.py`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/export_sample_contracts.py`

- Category: `api_mobile_integration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/export_sample_contracts.py`
- Reference counts: ai_context=0, docs=0, tests=0, python=0, readme_setup=1
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- readme_setup: REPO_STRUCTURE.md

### `scripts/forecasting/build_optional_pv_tables.py`

- Category: `forecasting`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_optional_pv_tables.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/forecasting/build_price_15min.py`

- Category: `forecasting`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_price_15min.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/generate_synthetic_live_requests.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/generate_synthetic_live_requests.py`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md, docs/ai_context/REQUEST_FLOW.md

### `scripts/inject_live_request.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/inject_live_request.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=2
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- readme_setup: README.md, REPO_STRUCTURE.md

### `scripts/maps/build_dundee_interactive_maps.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=0, python=1, readme_setup=1
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- python: scripts/build_dundee_interactive_maps.py
- readme_setup: REPO_STRUCTURE.md

### `scripts/maps/build_dundee_osmnx_graph.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=2, python=4, readme_setup=0
- Evidence: Found 8 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py
- python: scripts/build_dundee_osmnx_graph.py, scripts/maps/evaluate_osmnx_routing_usefulness.py, scripts/maps/export_osmnx_route_preview.py, scripts/maps/verify_osmnx_routing_provider.py

### `scripts/maps/evaluate_osmnx_routing_usefulness.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md
- python: scripts/evaluate_osmnx_routing_usefulness.py

### `scripts/maps/export_osmnx_route_preview.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/DATA_ARTIFACTS_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md
- python: scripts/export_osmnx_route_preview.py

### `scripts/maps/verify_osmnx_routing_provider.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md
- python: scripts/verify_osmnx_routing_provider.py

### `scripts/maps/verify_routing_provider.py`

- Category: `routing_maps`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/RECOMMENDER_FLOW.md
- python: scripts/verify_routing_provider.py

### `scripts/rl_training/analyze_rl_demand_realism.py`

- Category: `rl_training`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `False`
- Reference counts: ai_context=2, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RL_READINESS_REPORT.md
- python: scripts/analyze_rl_demand_realism.py

### `scripts/rl_training/verify_rl_env_skeleton.py`

- Category: `rl_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=2, python=1, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py
- python: scripts/verify_rl_env_skeleton.py

### `scripts/rl_training/verify_rl_scenario_sampler.py`

- Category: `rl_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- python: scripts/verify_rl_scenario_sampler.py

### `scripts/run_demo_runtime.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/run_demo_runtime.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=2
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- readme_setup: README.md, REPO_STRUCTURE.md

### `scripts/seed_stations.py`

- Category: `data_build`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/data/seed_stations.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md

### `scripts/smoke_mobile_lifecycle.sh`

- Category: `api_mobile_integration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/smoke_mobile_lifecycle.sh`
- Reference counts: ai_context=0, docs=0, tests=1, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- tests: tests/architecture/test_script_audit.py

### `scripts/verification/smoke_mobile_lifecycle.sh`

- Category: `api_mobile_integration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=1, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- tests: tests/architecture/test_script_audit.py
- python: scripts/smoke_mobile_lifecycle.sh

### `scripts/verification/verify_app_pricing_duration_alignment.py`

- Category: `pricing_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md
- python: scripts/verify_app_pricing_duration_alignment.py

### `scripts/verification/verify_dashboard_smoke.py`

- Category: `dashboard_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=0, docs=0, tests=2, python=1, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py
- python: scripts/verify_dashboard_smoke.py

### `scripts/verification/verify_dundee_tariff_pricing.py`

- Category: `pricing_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md
- python: scripts/verify_dundee_tariff_pricing.py

### `scripts/verification/verify_dynamic_pricing.py`

- Category: `pricing_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md
- python: scripts/verify_dynamic_pricing.py

### `scripts/verification/verify_station_access.py`

- Category: `topology_calibration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=2, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md
- python: scripts/verify_station_access.py

### `scripts/verification/verify_synthetic_live_requests.py`

- Category: `general_verification`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=3, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 4 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/REQUEST_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md
- python: scripts/verify_synthetic_live_requests.py

### `scripts/verification/verify_topology_scenario.py`

- Category: `topology_calibration`
- Entrypoint kind: `grouped_implementation`
- Recommended action: `keep`
- Known manual CLI: `True`
- Reference counts: ai_context=1, docs=0, tests=0, python=1, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- python: scripts/verify_topology_scenario.py

### `scripts/verify_app_pricing_duration_alignment.py`

- Category: `pricing_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_app_pricing_duration_alignment.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md

### `scripts/verify_app_runtime_integration.py`

- Category: `api_mobile_integration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/verify_app_runtime_integration.py`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_dashboard_smoke.py`

- Category: `dashboard_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_dashboard_smoke.py`
- Reference counts: ai_context=0, docs=0, tests=2, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py

### `scripts/verify_dundee_tariff_pricing.py`

- Category: `pricing_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_dundee_tariff_pricing.py`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_dynamic_pricing.py`

- Category: `pricing_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_dynamic_pricing.py`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_osmnx_routing_provider.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/maps/verify_osmnx_routing_provider.py`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/verify_rl_env_skeleton.py`

- Category: `rl_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/rl_training/verify_rl_env_skeleton.py`
- Reference counts: ai_context=1, docs=0, tests=2, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py

### `scripts/verify_rl_scenario_sampler.py`

- Category: `rl_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/rl_training/verify_rl_scenario_sampler.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md

### `scripts/verify_routing_provider.py`

- Category: `routing_maps`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/maps/verify_routing_provider.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/verify_runtime_liveness.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/verify_runtime_liveness.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/OPEN_QUESTIONS.md

### `scripts/verify_runtime_smoke.py`

- Category: `digital_twin_runtime`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/digital_twin/verify_runtime_smoke.py`
- Reference counts: ai_context=3, docs=0, tests=2, python=0, readme_setup=0
- Evidence: Found 5 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md
- tests: tests/architecture/test_script_audit.py, tests/architecture/test_script_grouping.py

### `scripts/verify_station_access.py`

- Category: `topology_calibration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_station_access.py`
- Reference counts: ai_context=2, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 2 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/RECOMMENDER_FLOW.md

### `scripts/verify_synthetic_live_requests.py`

- Category: `general_verification`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_synthetic_live_requests.py`
- Reference counts: ai_context=3, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 3 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md, docs/ai_context/REQUEST_FLOW.md, docs/ai_context/RL_READINESS_REPORT.md

### `scripts/verify_topology_scenario.py`

- Category: `topology_calibration`
- Entrypoint kind: `legacy_wrapper`
- Recommended action: `keep`
- Known manual CLI: `True`
- Wrapper target: `scripts/verification/verify_topology_scenario.py`
- Reference counts: ai_context=1, docs=0, tests=0, python=0, readme_setup=0
- Evidence: Found 1 reference(s) across repo search targets.
- Evidence: Name matches a likely manual CLI or verification entrypoint.
- Evidence: Keep in place for this PR; future grouping can be evaluated in a follow-up PR.
- ai_context_docs: docs/ai_context/CURRENT_IMPLEMENTATION_MAP.md

## Known Warning

- No unreadable `outputs/runtime` path was encountered during this audit run.

