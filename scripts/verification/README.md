# Verification Scripts

This folder holds general verification entrypoints that are not specific enough for another workflow bucket.

Use these scripts for dashboard, pricing, topology, station-access, and app-alignment checks.

## RL safety preference ranking

The non-strict verifier exercises deterministic synthetic cases without loading
the optional ML stack:

```powershell
uv run --with pydantic --with numpy --with pandas python scripts\verification\verify_rl_safety_preference_ranking.py
```

The strict verifier also requires the feeder checkpoint and local replay
artifacts under `data/processed/evside_feeder_rl`:

```powershell
uv run --with pyarrow --with pydantic --with numpy --with torch --with stable-baselines3 --with sb3-contrib python scripts\verification\verify_rl_safety_preference_ranking.py --strict
```

Strict success requires real checkpoint inference with no fallback. The stable
ordinal bridge remains nonphysical app/demo mapping; primary grid-performance
evidence remains feeder-evaluator evidence.

## Deployment artifacts

Check that the strict feeder RL metadata, parquet data, and checkpoint are
present:

```powershell
python scripts\verification\check_deployment_artifacts.py
python scripts\verification\check_deployment_artifacts.py --json
uv run --with pandas --with pyarrow python scripts\verification\check_deployment_artifacts.py --json --check-parquet
```

The checker reports only repository-relative paths and rejects unmaterialized
Git LFS pointer files. Run `git lfs pull` after cloning before strict startup.

## Tracked text health

Audit tracked source, test, configuration, script, and documentation files for
null bytes and invalid UTF-8, and compile every audited Python file:

```powershell
python scripts\verification\audit_tracked_text_files.py
```

The audit reads paths from `git ls-files`. Generated data trees, ignored feeder
artifacts, model files, generated outputs, and caches are not parsed as source
text; data artifacts need their own format/readability validation.
