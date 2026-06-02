# Scripts

Scripts are now grouped by workflow under:

- `scripts/data/`
- `scripts/digital_twin/`
- `scripts/maps/`
- `scripts/verification/`
- `scripts/rl_training/`
- `scripts/forecasting/`
- `scripts/benchmarks/`

Legacy root-level script paths are kept temporarily as backward-compatible wrappers so existing commands, docs, and tests keep working while migration is in progress.

The current audit and conservative cleanup guidance live in `docs/ai_context/SCRIPT_AND_FILE_AUDIT.md`.

Do not move or delete scripts without checking that audit first. Deletion requires:

1. no references in docs, tests, or code
2. confirmation that the script is not a useful manual CLI
3. evidence that a newer script replaced it
4. passing tests without it
5. user approval

Common verification commands:

```powershell
uv run --with pytest --with pydantic --with pandas --with numpy pytest tests/architecture -q
uv run --with pytest --with pydantic --with pandas --with numpy pytest tests -q
uv run --with gymnasium --with pytest --with pydantic --with pandas --with numpy pytest tests/rl -q
uv run --with pydantic --with pandas --with numpy python scripts/audit_repo_entrypoints.py --output docs/ai_context/SCRIPT_AND_FILE_AUDIT.md
```
