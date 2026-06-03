from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
GROUP_DIRS = [
    "data",
    "digital_twin",
    "maps",
    "verification",
    "rl_training",
    "forecasting",
    "benchmarks",
]
IMPORTANT_WRAPPERS = {
    "verify_runtime_smoke.py": "digital_twin/verify_runtime_smoke.py",
    "verify_dashboard_smoke.py": "verification/verify_dashboard_smoke.py",
    "build_dundee_osmnx_graph.py": "maps/build_dundee_osmnx_graph.py",
    "verify_rl_env_skeleton.py": "rl_training/verify_rl_env_skeleton.py",
}


def test_grouped_script_folders_exist_with_readmes() -> None:
    for folder in GROUP_DIRS:
        folder_path = SCRIPTS_ROOT / folder
        assert folder_path.is_dir(), folder_path
        assert (folder_path / "README.md").is_file(), folder_path / "README.md"


def test_important_old_wrapper_paths_still_exist_and_target_grouped_scripts() -> None:
    for wrapper_name, target_suffix in IMPORTANT_WRAPPERS.items():
        wrapper_path = SCRIPTS_ROOT / wrapper_name
        assert wrapper_path.is_file(), wrapper_path

        wrapper_text = wrapper_path.read_text(encoding="utf-8")
        assert "Backward-compatible entrypoint" in wrapper_text
        assert f"Wrapper target: scripts/{target_suffix}" in wrapper_text

        target_path = SCRIPTS_ROOT / target_suffix
        assert target_path.is_file(), target_path


def test_grouped_readmes_and_wrappers_do_not_require_heavy_imports() -> None:
    banned = ("fastapi", "streamlit", "gymnasium", "stable_baselines3", "sb3_contrib")
    for folder in GROUP_DIRS:
        readme_text = (SCRIPTS_ROOT / folder / "README.md").read_text(encoding="utf-8")
        lowered = readme_text.lower()
        for name in banned:
            assert name not in lowered

    for wrapper_name in IMPORTANT_WRAPPERS:
        wrapper_text = (SCRIPTS_ROOT / wrapper_name).read_text(encoding="utf-8").lower()
        for name in banned:
            assert name not in wrapper_text


def test_audit_script_runs_after_grouping() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_ROOT / "audit_repo_entrypoints.py"),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert "legacy_wrapper" in result.stdout
