"""Audit tracked text files for common repository-corruption signatures."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = frozenset(
    {
        ".bat",
        ".cfg",
        ".css",
        ".csv",
        ".env",
        ".example",
        ".html",
        ".ini",
        ".js",
        ".json",
        ".jsx",
        ".md",
        ".ps1",
        ".py",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)
TEXT_FILENAMES = frozenset(
    {
        ".gitattributes",
        ".gitignore",
        "Dockerfile",
        "Makefile",
    }
)
GENERATED_DATA_PREFIXES = frozenset(
    {
        ("data", "interim"),
        ("data", "processed"),
        ("data", "raw"),
    }
)


@dataclass(frozen=True)
class AuditFailure:
    path: Path
    kind: str
    detail: str


def is_auditable_path(path: Path) -> bool:
    parts = tuple(part.lower() for part in path.parts)
    if len(parts) >= 2 and parts[:2] in GENERATED_DATA_PREFIXES:
        return False
    return path.name in TEXT_FILENAMES or path.suffix.lower() in TEXT_SUFFIXES


def audit_path(
    path: Path,
    *,
    display_path: Path | None = None,
) -> list[AuditFailure]:
    shown_path = display_path or path
    try:
        content = path.read_bytes()
    except OSError as exc:
        return [AuditFailure(shown_path, "read_error", str(exc))]

    if b"\x00" in content:
        return [
            AuditFailure(
                shown_path,
                "null_bytes",
                "file contains at least one null byte",
            )
        ]

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return [
            AuditFailure(
                shown_path,
                "utf8_decode",
                f"invalid UTF-8 at byte {exc.start}",
            )
        ]

    if shown_path.suffix.lower() != ".py":
        return []

    try:
        compile(text, shown_path.as_posix(), "exec", dont_inherit=True)
    except SyntaxError as exc:
        line = exc.lineno or 0
        detail = f"{exc.msg} at line {line}"
        if exc.offset is not None:
            detail += f", column {exc.offset}"
        return [AuditFailure(shown_path, "python_syntax", detail)]
    return []


def tracked_text_paths(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    tracked = (
        Path(item.decode("utf-8"))
        for item in result.stdout.split(b"\x00")
        if item
    )
    return sorted(path for path in tracked if is_auditable_path(path))


def audit_repository(
    repo_root: Path,
) -> tuple[list[Path], list[AuditFailure]]:
    paths = tracked_text_paths(repo_root)
    failures: list[AuditFailure] = []
    for relative_path in paths:
        failures.extend(
            audit_path(
                repo_root / relative_path,
                display_path=relative_path,
            )
        )
    return paths, failures


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Git working tree to audit (default: this repository).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        paths, failures = audit_repository(repo_root)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        print(f"AUDIT_ERROR {exc}")
        return 2

    if failures:
        print(
            f"AUDIT_FAILED tracked_text_files={len(paths)} "
            f"failures={len(failures)}"
        )
        for failure in failures:
            print(
                f"{failure.path.as_posix()}: "
                f"{failure.kind}: {failure.detail}"
            )
        return 1

    print(f"AUDIT_OK tracked_text_files={len(paths)} failures=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
