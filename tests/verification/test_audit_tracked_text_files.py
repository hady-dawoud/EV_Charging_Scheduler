from __future__ import annotations

from pathlib import Path

from scripts.verification.audit_tracked_text_files import (
    audit_path,
    is_auditable_path,
)


def test_audit_path_accepts_valid_utf8_python(tmp_path: Path) -> None:
    path = tmp_path / "healthy.py"
    path.write_text("value = 42\n", encoding="utf-8")

    assert audit_path(path, display_path=Path("healthy.py")) == []


def test_audit_path_rejects_null_bytes(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.md"
    path.write_bytes(b"healthy\x00corrupt\n")

    failures = audit_path(path, display_path=Path("corrupt.md"))

    assert len(failures) == 1
    assert failures[0].kind == "null_bytes"
    assert failures[0].path == Path("corrupt.md")


def test_audit_path_rejects_invalid_utf8(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.txt"
    path.write_bytes(b"\xff\xfeinvalid")

    failures = audit_path(path, display_path=Path("corrupt.txt"))

    assert len(failures) == 1
    assert failures[0].kind == "utf8_decode"


def test_audit_path_rejects_python_syntax_errors(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.py"
    path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    failures = audit_path(path, display_path=Path("corrupt.py"))

    assert len(failures) == 1
    assert failures[0].kind == "python_syntax"
    assert "line 1" in failures[0].detail


def test_generated_data_trees_are_not_source_text_audit_targets() -> None:
    assert is_auditable_path(
        Path("data/processed/station_capacity_assumptions.csv")
    ) is False
    assert is_auditable_path(Path("scripts/data/build_inputs.py")) is True
