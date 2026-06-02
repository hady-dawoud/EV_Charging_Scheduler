from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_repo_entrypoints.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_repo_entrypoints", AUDIT_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Failed to create module spec for audit_repo_entrypoints.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_import(code: str) -> subprocess.CompletedProcess[str]:
    pythonpath = str(REPO_ROOT / "packages" / "ev_core" / "src")
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": pythonpath,
        },
    )


def test_audit_module_import_is_dependency_light() -> None:
    code = f"""
import importlib.util
import pathlib
import sys

path = pathlib.Path(r"{AUDIT_SCRIPT_PATH}")
spec = importlib.util.spec_from_file_location("audit_repo_entrypoints", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for banned in [
    "fastapi",
    "streamlit",
    "gymnasium",
    "stable_baselines3",
    "sb3_contrib",
]:
    if banned in sys.modules:
        raise RuntimeError(f"banned module imported: {{banned}}")
print("ok")
"""
    result = _run_import(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_classify_entrypoint_assigns_expected_categories() -> None:
    module = _load_audit_module()

    assert module.classify_entrypoint("verify_runtime_smoke.py") in {
        "digital_twin_runtime",
        "general_verification",
    }
    assert module.classify_entrypoint("verify_dashboard_smoke.py") == "dashboard_verification"
    assert module.classify_entrypoint("build_dundee_osmnx_graph.py") == "routing_maps"
    assert module.classify_entrypoint("verify_rl_env_skeleton.py") == "rl_verification"


def test_scan_repo_entrypoints_can_scan_temporary_scripts_folder(tmp_path: Path) -> None:
    module = _load_audit_module()

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "verify_runtime_smoke.py").write_text("print('ok')\n", encoding="utf-8")
    (scripts_dir / "smoke_mobile_lifecycle.sh").write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Use scripts/verify_runtime_smoke.py\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("smoke_mobile_lifecycle.sh\n", encoding="utf-8")

    report = module.scan_repo_entrypoints(
        repo_root=tmp_path,
        entrypoint_roots=[scripts_dir],
        reference_roots=[tmp_path],
    )

    names = {entry.path.name for entry in report.entries}
    assert "verify_runtime_smoke.py" in names
    assert "smoke_mobile_lifecycle.sh" in names


def test_json_output_is_valid(tmp_path: Path) -> None:
    module = _load_audit_module()

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "verify_runtime_smoke.py").write_text("print('ok')\n", encoding="utf-8")

    report = module.scan_repo_entrypoints(
        repo_root=tmp_path,
        entrypoint_roots=[scripts_dir],
        reference_roots=[tmp_path],
    )
    payload = module.render_json_report(report)
    parsed = json.loads(payload)

    assert parsed["summary"]["script_count"] == 1
    assert parsed["entries"][0]["name"] == "verify_runtime_smoke.py"


def test_markdown_output_contains_summary_and_category_names(tmp_path: Path) -> None:
    module = _load_audit_module()

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "verify_dashboard_smoke.py").write_text("print('ok')\n", encoding="utf-8")

    report = module.scan_repo_entrypoints(
        repo_root=tmp_path,
        entrypoint_roots=[scripts_dir],
        reference_roots=[tmp_path],
    )
    markdown = module.render_markdown_report(report)

    assert "# Script And File Audit" in markdown
    assert "## Summary" in markdown
    assert "dashboard_verification" in markdown
