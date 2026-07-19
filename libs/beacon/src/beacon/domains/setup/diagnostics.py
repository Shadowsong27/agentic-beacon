"""Project-side diagnostic checks for abc doctor.

Implements checks that need a project root (not a warehouse root):
- Symlink hygiene under .agentic-beacon/artifacts/
- @path reference integrity in CLAUDE.md / opencode.json
- Stale beacon.yaml globs
- Sanity checks (warehouse git, platform)
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from beacon.core.gitignore import apply_all_gitignores, diff_gitignores
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.distribution.sync_engine import SyncEngine


@dataclass(frozen=True)
class DoctorIssue:
    """A single diagnostic issue with optional detail."""

    message: str
    detail: str = ""
    severity: str = "error"  # "error" or "warn"


def repair_gitignore_drift(project_root: Path) -> list[str]:
    """Repair managed-block gitignore drift in place (Tier A / Tier B).

    Returns human-readable descriptions of the fixes applied (empty if none).
    Non-fixable drift (tracked_set_ignored — a user pattern ignoring a
    tracked-on-purpose file) is NOT touched here; it is left for
    _check_gitignore_drift to report as remaining drift.
    """
    if not (project_root / ".agentic-beacon" / "beacon.yaml").exists():
        return []
    drifts = diff_gitignores(project_root)
    managed_kinds = {
        "tier_a_missing",
        "tier_a_incomplete",
        "tier_b_missing",
        "tier_b_incomplete",
    }
    if any(d.kind in managed_kinds for d in drifts):
        apply_all_gitignores(project_root)
        return ["Repaired gitignore managed blocks (Tier A / Tier B)"]
    return []


def run_project_health_checks(
    project_root: Path,
    warehouse_path: Path | None,
    beacon_manifest: BeaconManifest | None,
) -> list[DoctorIssue]:
    """Run all project-side diagnostic checks.

    Returns a list of DoctorIssue records.  The caller (CLI layer) decides how
    to render them so the domain stays free of Rich/Click.
    """
    issues: list[DoctorIssue] = []

    if warehouse_path is not None:
        issues.extend(_check_symlink_hygiene(project_root, warehouse_path))
        issues.extend(_check_stale_globs(warehouse_path, beacon_manifest))
        issues.extend(_check_warehouse_git(warehouse_path))

    issues.extend(_check_path_references(project_root, beacon_manifest))
    issues.extend(_check_gitignore_drift(project_root))
    issues.extend(_check_platform())

    return issues


# ---------------------------------------------------------------------------
# Check 1: Symlink hygiene
# ---------------------------------------------------------------------------


_GLOB_CHARS = frozenset("*?[]")


def _is_glob_pattern(path: str) -> bool:
    return any(ch in path for ch in _GLOB_CHARS)


def _check_symlink_hygiene(
    project_root: Path, warehouse_path: Path
) -> list[DoctorIssue]:
    artifacts_path = project_root / ".agentic-beacon" / "artifacts"
    if not artifacts_path.exists():
        return []

    issues: list[DoctorIssue] = []
    resolved_warehouse = warehouse_path.resolve()

    for path in sorted(artifacts_path.rglob("*")):
        if path.is_symlink():
            try:
                target = path.readlink()
            except OSError:
                continue

            if target.is_absolute():
                resolved_target = target.resolve()
            else:
                resolved_target = (path.parent / target).resolve()

            # Dangling symlink
            if not resolved_target.exists():
                rel = str(path.relative_to(artifacts_path))
                issues.append(
                    DoctorIssue(
                        message=f"Dangling symlink: {rel}",
                        detail=f"Target missing: {target}",
                        severity="error",
                    )
                )
                continue

            # Symlink pointing outside warehouse
            try:
                resolved_target.relative_to(resolved_warehouse)
            except ValueError:
                rel = str(path.relative_to(artifacts_path))
                issues.append(
                    DoctorIssue(
                        message=f"Symlink outside warehouse: {rel}",
                        detail=f"Target: {resolved_target}",
                        severity="error",
                    )
                )

        elif path.is_file():
            rel = str(path.relative_to(artifacts_path))
            issues.append(
                DoctorIssue(
                    message=f"Regular file where symlink should be: {rel}",
                    detail="Expected a symlink to the warehouse",
                    severity="error",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Check 2: @path references
# ---------------------------------------------------------------------------


_ATPATH_RE = re.compile(r"^@(.+)$")


def _check_path_references(
    project_root: Path,
    beacon_manifest: BeaconManifest | None,
) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []

    # CLAUDE.md
    for claude_md in (
        project_root / ".claude" / "CLAUDE.md",
        project_root / "CLAUDE.md",
    ):
        if claude_md.exists():
            issues.extend(_check_claude_md(claude_md, project_root, beacon_manifest))

    # opencode.json
    for opencode_json in (
        project_root / ".opencode" / "opencode.json",
        project_root / "opencode.json",
    ):
        if opencode_json.exists():
            issues.extend(
                _check_opencode_json(opencode_json, project_root, beacon_manifest)
            )

    # .claude/settings.json (defensive — not used by current wiring but may exist)
    settings_json = project_root / ".claude" / "settings.json"
    if settings_json.exists():
        issues.extend(
            _check_opencode_json(settings_json, project_root, beacon_manifest)
        )

    return issues


def _check_claude_md(
    claude_md: Path,
    project_root: Path,
    beacon_manifest: BeaconManifest | None,
) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    try:
        content = claude_md.read_text(encoding="utf-8")
    except OSError:
        return issues

    for line in content.splitlines():
        line = line.strip()
        match = _ATPATH_RE.match(line)
        if not match:
            continue

        raw_path = match.group(1).strip()
        if not raw_path:
            continue

        issue = _classify_reference(
            raw_path, project_root, beacon_manifest, str(claude_md)
        )
        if issue:
            issues.append(issue)

    return issues


def _check_opencode_json(
    json_path: Path,
    project_root: Path,
    beacon_manifest: BeaconManifest | None,
) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return issues

    instructions = data.get("instructions", []) if isinstance(data, dict) else []
    if not isinstance(instructions, list):
        return issues

    for item in instructions:
        if not isinstance(item, str):
            continue
        if "/" not in item and "\\" not in item:
            continue
        issue = _classify_reference(item, project_root, beacon_manifest, str(json_path))
        if issue:
            issues.append(issue)

    return issues


def _classify_reference(
    raw_path: str,
    project_root: Path,
    beacon_manifest: BeaconManifest | None,
    source_file: str,
) -> DoctorIssue | None:
    """Classify a single @path/reference and return an Issue or None."""

    # Absolute paths in project-committed config are not portable across machines.
    if raw_path.startswith("/"):
        return DoctorIssue(
            message=f"Non-portable absolute path in {Path(source_file).name}",
            detail=f"{raw_path} is an absolute path and will break for other teammates",
            severity="error",
        )

    # Resolve relative to project root
    candidate = project_root / raw_path
    # Also try under artifacts/ if the path looks like a bare artifact reference
    if not candidate.exists() and not raw_path.startswith(".agentic-beacon"):
        candidate = project_root / ".agentic-beacon" / "artifacts" / raw_path

    if not candidate.exists():
        return DoctorIssue(
            message=f"Broken reference in {Path(source_file).name}",
            detail=f"{raw_path} does not exist",
            severity="error",
        )

    # If the reference doesn't appear to target a warehouse artifact, treat it
    # as a project-local file: report only "missing" if it doesn't exist,
    # never "unmanaged."
    looks_like_artifact = (
        raw_path.startswith(".agentic-beacon/artifacts/")
        or (project_root / ".agentic-beacon" / "artifacts" / raw_path).exists()
    )
    if not looks_like_artifact:
        return None

    # Path exists locally — check if it's wired in beacon.yaml
    if beacon_manifest is not None:
        wired = _is_wired_in_beacon(raw_path, beacon_manifest)
        if not wired:
            return DoctorIssue(
                message=f"Unmanaged reference in {Path(source_file).name}",
                detail=f"{raw_path} exists but is not listed in beacon.yaml",
                severity="warn",
            )

    return None


def _is_wired_in_beacon(raw_path: str, beacon_manifest: BeaconManifest) -> bool:
    """Return True if the referenced path matches a beacon.yaml entry."""

    # Normalize: strip leading .agentic-beacon/artifacts/ if present
    normalized = raw_path
    prefix = ".agentic-beacon/artifacts/"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix) :]

    # Exact match against any artifact type
    for entry_list in (
        beacon_manifest.artifacts.skills,
        beacon_manifest.artifacts.contexts,
        beacon_manifest.artifacts.agents,
    ):
        for entry in entry_list:
            entry_stripped = entry.rstrip("/")
            norm_stripped = normalized.rstrip("/")
            if entry_stripped == norm_stripped:
                return True
            # Directory entry: path is under the entry
            if norm_stripped.startswith(entry_stripped + "/"):
                return True
            # Glob entry: match using fnmatch
            if _is_glob_pattern(entry_stripped) and fnmatch.fnmatchcase(
                norm_stripped, entry_stripped
            ):
                return True

    return False


# ---------------------------------------------------------------------------
# Check 3: Stale globs
# ---------------------------------------------------------------------------


def _check_stale_globs(
    warehouse_path: Path,
    beacon_manifest: BeaconManifest | None,
) -> list[DoctorIssue]:
    if beacon_manifest is None:
        return []

    issues: list[DoctorIssue] = []
    all_entries: list[tuple[str, list[str]]] = [
        ("skills", beacon_manifest.artifacts.skills),
        ("contexts", beacon_manifest.artifacts.contexts),
        ("agents", beacon_manifest.artifacts.agents),
    ]

    engine = SyncEngine(warehouse_path=warehouse_path, artifacts_path=Path())

    for artifact_type, entries in all_entries:
        for entry in entries:
            if not _is_glob_pattern(entry):
                continue
            matches = engine.expand_glob(entry)
            if not matches:
                issues.append(
                    DoctorIssue(
                        message=f"Stale glob in beacon.yaml ({artifact_type})",
                        detail=f"'{entry}' matches 0 files in warehouse",
                        severity="error",
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Check 4: Sanity checks
# ---------------------------------------------------------------------------


def _check_warehouse_git(warehouse_path: Path) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    if not (warehouse_path / ".git").exists():
        issues.append(
            DoctorIssue(
                message="Warehouse is not a git working tree",
                detail=f"{warehouse_path} missing .git directory",
                severity="warn",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Check 5: Gitignore drift
# ---------------------------------------------------------------------------


def _check_gitignore_drift(project_root: Path) -> list[DoctorIssue]:
    if not (project_root / ".agentic-beacon" / "beacon.yaml").exists():
        return []

    issues: list[DoctorIssue] = []
    drifts = diff_gitignores(project_root)
    for drift in drifts:
        issues.append(
            DoctorIssue(
                message=drift.message,
                detail=drift.detail,
                severity="error",
            )
        )
    return issues


def _check_platform() -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    plat = sys.platform
    if plat.startswith("win") or plat == "cygwin":
        issues.append(
            DoctorIssue(
                message="Windows platform detected",
                detail="Symlink-based artifact sync may not work correctly",
                severity="warn",
            )
        )
    return issues
