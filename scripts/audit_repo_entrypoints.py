"""Audit repo entrypoints and conservative cleanup candidates."""

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Iterable


SCRIPT_CATEGORIES = (
    "data_build",
    "digital_twin_runtime",
    "api_mobile_integration",
    "dashboard_verification",
    "pricing_verification",
    "routing_maps",
    "topology_calibration",
    "rl_training",
    "rl_verification",
    "forecasting",
    "benchmarking",
    "general_verification",
    "legacy_or_unknown",
    "candidate_for_delete",
    "candidate_for_move",
)

ENTRYPOINT_SUFFIXES = {".py", ".sh", ".ps1", ".bat", ".cmd"}
REFERENCE_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".tsx",
    ".ts",
    ".js",
}
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".uv-cache",
}
ROOT_REFERENCE_FILES = {
    "README.md",
    "DEVELOPMENT_SETUP.md",
    "REPO_STRUCTURE.md",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile.api",
    "Dockerfile.dashboard",
    "Dockerfile.mobile",
    "pyproject.toml",
}
ROOT_ENTRYPOINT_PREFIXES = (
    "build_",
    "verify_",
    "run_",
    "inject_",
    "generate_",
    "export_",
    "evaluate_",
    "clean_",
    "seed_",
    "audit_",
    "smoke_",
)
GROUPED_SCRIPT_FOLDERS = (
    "data",
    "digital_twin",
    "maps",
    "verification",
    "rl_training",
    "forecasting",
    "benchmarks",
)


@dataclass
class ReferenceMatches:
    ai_context_docs: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    python: list[str] = field(default_factory=list)
    readme_setup: list[str] = field(default_factory=list)

    def total_count(self) -> int:
        return sum(len(items) for items in asdict(self).values())


@dataclass
class AuditEntry:
    path: Path
    category: str
    entrypoint_kind: str
    wrapper_target_path: str | None
    references: ReferenceMatches
    known_manual_cli: bool
    recommended_action: str
    evidence: list[str]


@dataclass
class AuditSummary:
    script_count: int
    category_counts: dict[str, int]
    scripts_with_no_references: list[str]
    scripts_recommended_to_keep: list[str]
    scripts_needing_human_review: list[str]
    scripts_safe_to_delete_later: list[str]


@dataclass
class AuditReport:
    repo_root: Path
    entries: list[AuditEntry]
    summary: AuditSummary
    warnings: list[str]
    grouped_folders: list[str]


def classify_entrypoint(name: str) -> str:
    lowered = name.lower()
    if lowered.startswith(("build_", "clean_", "seed_")):
        if "osmnx" in lowered or "map" in lowered:
            return "routing_maps"
        if "topology" in lowered or "transformer" in lowered:
            return "topology_calibration"
        if "price" in lowered or "pv" in lowered or "forecast" in lowered:
            return "forecasting"
        return "data_build"
    if lowered.startswith("calibrate_"):
        return "topology_calibration"
    if lowered.startswith("generate_"):
        if "synthetic_live" in lowered:
            return "digital_twin_runtime"
        return "data_build"
    if lowered.startswith("export_"):
        if "route" in lowered or "osmnx" in lowered:
            return "routing_maps"
        return "api_mobile_integration"
    if lowered.startswith("evaluate_"):
        if "routing" in lowered or "osmnx" in lowered or "route" in lowered:
            return "routing_maps"
        if "rl" in lowered:
            return "rl_training"
        return "benchmarking"
    if lowered.startswith("smoke_"):
        return "api_mobile_integration"
    if lowered.startswith(("run_demo", "inject_live_request", "audit_repo")):
        return "digital_twin_runtime"
    if lowered.startswith("verify_"):
        if "dashboard" in lowered:
            return "dashboard_verification"
        if "pricing" in lowered or "tariff" in lowered:
            return "pricing_verification"
        if "routing" in lowered or "osmnx" in lowered or "route" in lowered or "map" in lowered:
            return "routing_maps"
        if "topology" in lowered or "transformer" in lowered or "station_access" in lowered:
            return "topology_calibration"
        if "app_" in lowered or "mobile" in lowered:
            return "api_mobile_integration"
        if lowered.startswith("verify_rl_") or "_rl_" in lowered:
            return "rl_verification"
        if "runtime" in lowered:
            return "digital_twin_runtime"
        return "general_verification"
    if "rl" in lowered:
        return "rl_training"
    if "benchmark" in lowered:
        return "benchmarking"
    return "legacy_or_unknown"


def is_known_manual_cli(path: Path) -> bool:
    lowered = path.name.lower()
    return lowered.startswith(ROOT_ENTRYPOINT_PREFIXES) or lowered.startswith(("verify_", "run_", "inject_"))


def _iter_entrypoints(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in ENTRYPOINT_SUFFIXES:
            yield path


def discover_entrypoints(repo_root: Path, entrypoint_roots: list[Path] | None = None) -> list[Path]:
    if entrypoint_roots is None:
        entrypoint_roots = [repo_root / "scripts"]

    discovered: dict[str, Path] = {}
    for root in entrypoint_roots:
        for path in _iter_entrypoints(root):
            discovered[str(path.resolve())] = path
    return sorted(discovered.values())


def discover_grouped_folders(repo_root: Path) -> list[str]:
    scripts_root = repo_root / "scripts"
    discovered: list[str] = []
    for folder in GROUPED_SCRIPT_FOLDERS:
        if (scripts_root / folder).is_dir():
            discovered.append(folder)
    return discovered


def _is_reference_file(repo_root: Path, path: Path) -> bool:
    if path.suffix.lower() not in REFERENCE_SUFFIXES:
        return False

    relative = path.relative_to(repo_root)
    if relative.parts and relative.parts[0] in {"docs", "tests", "packages", "apps", "services", "scripts"}:
        return True
    return path.name in ROOT_REFERENCE_FILES


def iter_reference_files(repo_root: Path, roots: list[Path] | None = None) -> tuple[list[Path], list[str]]:
    if roots is None:
        roots = [
            repo_root / "docs",
            repo_root / "tests",
            repo_root / "packages",
            repo_root / "apps",
            repo_root / "services",
            repo_root / "scripts",
            repo_root,
        ]

    files: dict[str, Path] = {}
    warnings: list[str] = []
    seen_root = False

    for root in roots:
        if not root.exists():
            continue
        if root == repo_root:
            seen_root = True
            for path in sorted(repo_root.iterdir()):
                if path.is_file() and _is_reference_file(repo_root, path):
                    files[str(path.resolve())] = path
            continue

        for current_root, dir_names, file_names in root.walk(on_error=lambda error: warnings.append(str(error))):
            dir_names[:] = [
                name
                for name in dir_names
                if name not in SKIP_DIR_NAMES and not name.startswith(".tmp")
            ]
            current_root_path = Path(current_root)
            for file_name in file_names:
                candidate = current_root_path / file_name
                if _is_reference_file(repo_root, candidate):
                    files[str(candidate.resolve())] = candidate

    if not seen_root:
        for path in sorted(repo_root.iterdir()):
            if path.is_file() and _is_reference_file(repo_root, path):
                files[str(path.resolve())] = path
    return sorted(files.values()), warnings


def _bucket_for_reference(repo_root: Path, path: Path) -> str:
    relative = path.relative_to(repo_root)
    first = relative.parts[0] if relative.parts else ""
    if first == "docs" and len(relative.parts) > 1 and relative.parts[1] == "ai_context":
        return "ai_context_docs"
    if first == "docs":
        return "docs"
    if first == "tests":
        return "tests"
    if first in {"packages", "apps", "services", "scripts"}:
        return "python"
    return "readme_setup"


def _search_terms(entrypoint: Path, repo_root: Path) -> list[str]:
    relative = entrypoint.relative_to(repo_root).as_posix()
    terms = [entrypoint.name.lower(), relative.lower()]
    if relative.startswith("scripts/"):
        terms.append(relative.replace("/", "\\").lower())
    return list(dict.fromkeys(terms))


def detect_wrapper_target(repo_root: Path, entrypoint: Path) -> str | None:
    try:
        content = entrypoint.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    marker = "# Wrapper target:"
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith(marker):
            target = stripped.removeprefix(marker).strip()
            if target:
                return target
    return None


def classify_entrypoint_kind(repo_root: Path, entrypoint: Path) -> tuple[str, str | None]:
    relative = entrypoint.relative_to(repo_root)
    wrapper_target = detect_wrapper_target(repo_root, entrypoint)
    if wrapper_target is not None:
        return "legacy_wrapper", wrapper_target
    if relative.parts[:2] and len(relative.parts) >= 2 and relative.parts[0] == "scripts" and relative.parts[1] in GROUPED_SCRIPT_FOLDERS:
        return "grouped_implementation", None
    return "root_entrypoint", None


def find_references(repo_root: Path, entrypoint: Path, reference_files: list[Path]) -> ReferenceMatches:
    matches = ReferenceMatches()
    terms = _search_terms(entrypoint, repo_root)

    for file_path in reference_files:
        if file_path == entrypoint:
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        if not any(term in content for term in terms):
            continue
        bucket = _bucket_for_reference(repo_root, file_path)
        relative = file_path.relative_to(repo_root).as_posix()
        getattr(matches, bucket).append(relative)
    return matches


def recommend_action(path: Path, category: str, references: ReferenceMatches, known_manual_cli: bool) -> tuple[str, list[str]]:
    evidence: list[str] = []
    reference_count = references.total_count()

    if reference_count == 0:
        evidence.append("No references found in docs/tests/code/setup search.")
    else:
        evidence.append(f"Found {reference_count} reference(s) across repo search targets.")

    if known_manual_cli:
        evidence.append("Name matches a likely manual CLI or verification entrypoint.")

    if category == "legacy_or_unknown":
        evidence.append("Category could not be inferred confidently from the filename.")
        return "needs_review", evidence

    if reference_count == 0 and not known_manual_cli and (
        "legacy" in path.name.lower() or "deprecated" in path.name.lower()
    ):
        evidence.append("Potential delete candidate only if replacement and test evidence are confirmed later.")
        return "candidate_for_delete", evidence

    if reference_count == 0 and not known_manual_cli:
        evidence.append("No references were found and the script does not look like a known manual CLI.")
        return "needs_review", evidence

    evidence.append("Keep in place for this PR; future grouping can be evaluated in a follow-up PR.")
    return "keep", evidence


def build_summary(entries: list[AuditEntry]) -> AuditSummary:
    category_counts = Counter(entry.category for entry in entries)
    scripts_with_no_references = sorted(
        entry.path.name for entry in entries if entry.references.total_count() == 0
    )
    scripts_recommended_to_keep = sorted(
        entry.path.name for entry in entries if entry.recommended_action == "keep"
    )
    scripts_needing_human_review = sorted(
        entry.path.name for entry in entries if entry.recommended_action == "needs_review"
    )
    scripts_safe_to_delete_later = sorted(
        entry.path.name for entry in entries if entry.recommended_action == "candidate_for_delete"
    )
    return AuditSummary(
        script_count=len(entries),
        category_counts=dict(sorted(category_counts.items())),
        scripts_with_no_references=scripts_with_no_references,
        scripts_recommended_to_keep=scripts_recommended_to_keep,
        scripts_needing_human_review=scripts_needing_human_review,
        scripts_safe_to_delete_later=scripts_safe_to_delete_later,
    )


def scan_repo_entrypoints(
    repo_root: Path,
    entrypoint_roots: list[Path] | None = None,
    reference_roots: list[Path] | None = None,
    excluded_reference_paths: list[Path] | None = None,
) -> AuditReport:
    repo_root = repo_root.resolve()
    entrypoints = discover_entrypoints(repo_root, entrypoint_roots=entrypoint_roots)
    reference_files, warnings = iter_reference_files(repo_root, roots=reference_roots)
    excluded_resolved = {path.resolve() for path in (excluded_reference_paths or [])}
    reference_files = [path for path in reference_files if path.resolve() not in excluded_resolved]

    entries: list[AuditEntry] = []
    for entrypoint in entrypoints:
        category = classify_entrypoint(entrypoint.name)
        entrypoint_kind, wrapper_target = classify_entrypoint_kind(repo_root, entrypoint)
        references = find_references(repo_root, entrypoint, reference_files)
        known_cli = is_known_manual_cli(entrypoint)
        action, evidence = recommend_action(entrypoint, category, references, known_cli)
        entries.append(
            AuditEntry(
                path=entrypoint,
                category=category,
                entrypoint_kind=entrypoint_kind,
                wrapper_target_path=wrapper_target,
                references=references,
                known_manual_cli=known_cli,
                recommended_action=action,
                evidence=evidence,
            )
        )

    return AuditReport(
        repo_root=repo_root,
        entries=entries,
        summary=build_summary(entries),
        warnings=warnings,
        grouped_folders=discover_grouped_folders(repo_root),
    )


def render_json_report(report: AuditReport) -> str:
    payload = {
        "repo_root": str(report.repo_root),
        "summary": asdict(report.summary),
        "entries": [
            {
                "name": entry.path.name,
                "path": entry.path.relative_to(report.repo_root).as_posix(),
                "category": entry.category,
                "entrypoint_kind": entry.entrypoint_kind,
                "wrapper_target_path": entry.wrapper_target_path,
                "known_manual_cli": entry.known_manual_cli,
                "recommended_action": entry.recommended_action,
                "references": asdict(entry.references),
                "evidence": entry.evidence,
            }
            for entry in report.entries
        ],
        "warnings": report.warnings,
        "grouped_folders": report.grouped_folders,
    }
    return json.dumps(payload, indent=2)


def _format_list(items: list[str]) -> list[str]:
    return items if items else ["None"]


def render_markdown_report(report: AuditReport) -> str:
    lines: list[str] = ["# Script And File Audit", ""]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Scripts scanned: {report.summary.script_count}")
    for category, count in report.summary.category_counts.items():
        lines.append(f"- `{category}`: {count}")
    wrapper_count = sum(1 for entry in report.entries if entry.entrypoint_kind == "legacy_wrapper")
    grouped_count = sum(1 for entry in report.entries if entry.entrypoint_kind == "grouped_implementation")
    lines.append(f"- Grouped implementation scripts: {grouped_count}")
    lines.append(f"- Legacy compatibility wrappers: {wrapper_count}")
    lines.append(f"- Scripts with no references: {len(report.summary.scripts_with_no_references)}")
    lines.append(f"- Scripts recommended to keep: {len(report.summary.scripts_recommended_to_keep)}")
    lines.append(f"- Scripts needing human review: {len(report.summary.scripts_needing_human_review)}")
    lines.append(f"- Scripts that look safe to delete later: {len(report.summary.scripts_safe_to_delete_later)}")
    lines.append("")

    lines.append("## Grouped Script Folders")
    lines.append("")
    for folder in _format_list([f"scripts/{folder}/" for folder in report.grouped_folders]):
        lines.append(f"- `{folder}`")
    lines.append("")

    lines.append("## Compatibility Wrappers")
    lines.append("")
    if wrapper_count:
        lines.append("- Legacy root-level script paths are kept as thin wrappers in this PR.")
        lines.append("- Wrappers are temporary compatibility entrypoints and should be removed only after docs and tests migrate.")
    else:
        lines.append("- No legacy compatibility wrappers were detected in this audit run.")
    lines.append("")

    lines.append("## Scripts With No References")
    lines.append("")
    for item in _format_list(report.summary.scripts_with_no_references):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Scripts Recommended To Keep")
    lines.append("")
    for item in _format_list(report.summary.scripts_recommended_to_keep):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Scripts Needing Human Review")
    lines.append("")
    for item in _format_list(report.summary.scripts_needing_human_review):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Scripts That Look Safe To Delete Later")
    lines.append("")
    for item in _format_list(report.summary.scripts_safe_to_delete_later):
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Proposed Future Script Grouping")
    lines.append("")
    lines.append("- `scripts/data/`")
    lines.append("- `scripts/digital_twin/`")
    lines.append("- `scripts/maps/`")
    lines.append("- `scripts/verification/`")
    lines.append("- `scripts/rl_training/`")
    lines.append("- `scripts/forecasting/`")
    lines.append("- `scripts/benchmarks/`")
    lines.append("")

    lines.append("## Candidate Cleanup Rules")
    lines.append("")
    lines.append("A file can only be deleted if:")
    lines.append("1. it is not referenced by docs, tests, or code")
    lines.append("2. it is not a useful manual CLI")
    lines.append("3. it has been clearly replaced by a newer script")
    lines.append("4. full tests pass without it")
    lines.append("5. the user approves deletion")
    lines.append("")

    lines.append("## Outputs/Test_Data Policy")
    lines.append("")
    lines.append("- `outputs/test_data` is intentionally kept for now.")
    lines.append("- Do not delete it in this PR.")
    lines.append("- A later PR may move stable fixtures to `tests/fixtures`.")
    lines.append("")

    lines.append("## Entry Details")
    lines.append("")
    for entry in report.entries:
        rel_path = entry.path.relative_to(report.repo_root).as_posix()
        lines.append(f"### `{rel_path}`")
        lines.append("")
        lines.append(f"- Category: `{entry.category}`")
        lines.append(f"- Entrypoint kind: `{entry.entrypoint_kind}`")
        lines.append(f"- Recommended action: `{entry.recommended_action}`")
        lines.append(f"- Known manual CLI: `{entry.known_manual_cli}`")
        if entry.wrapper_target_path is not None:
            lines.append(f"- Wrapper target: `{entry.wrapper_target_path}`")
        lines.append(
            "- Reference counts: "
            f"ai_context={len(entry.references.ai_context_docs)}, "
            f"docs={len(entry.references.docs)}, "
            f"tests={len(entry.references.tests)}, "
            f"python={len(entry.references.python)}, "
            f"readme_setup={len(entry.references.readme_setup)}"
        )
        for detail in entry.evidence:
            lines.append(f"- Evidence: {detail}")
        if entry.references.total_count() > 0:
            grouped_refs = {
                "ai_context_docs": entry.references.ai_context_docs,
                "docs": entry.references.docs,
                "tests": entry.references.tests,
                "python": entry.references.python,
                "readme_setup": entry.references.readme_setup,
            }
            for label, values in grouped_refs.items():
                if values:
                    lines.append(f"- {label}: {', '.join(values[:6])}")
        lines.append("")

    lines.append("## Known Warning")
    lines.append("")
    runtime_warnings = [warning for warning in report.warnings if "outputs\\runtime" in warning or "outputs/runtime" in warning]
    if runtime_warnings:
        lines.append("- Unreadable local artifact paths were encountered under `outputs/runtime`; treat them as local generated-state issues, not source code.")
    else:
        lines.append("- No unreadable `outputs/runtime` path was encountered during this audit run.")
    lines.append("")

    if report.warnings:
        lines.append("## Scan Warnings")
        lines.append("")
        for warning in report.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to scan.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of Markdown.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output file path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    excluded_reference_paths = [args.output] if args.output else None
    report = scan_repo_entrypoints(
        repo_root=args.repo_root,
        excluded_reference_paths=excluded_reference_paths,
    )
    rendered = render_json_report(report) if args.json else render_markdown_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
