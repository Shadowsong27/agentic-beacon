# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Summarize dirty warehouse paths for the contribute-warehouse skill.

# Self-contained script -- no beacon package required at runtime.

By default (PER-202), enumerates EVERY dirty path under the warehouse working
tree via `git status --porcelain`, regardless of project context. Pass
`--only-project-artifacts` to fall back to the legacy beacon.yaml-filtered
behavior.

Outputs a single JSON object on stdout:
  {"tracked_paths": [{"path": str, "git_status": str, "diff_stat": str,
                      "last_commit_age_days": int|null,
                      "warehouse_area": str}]}

Only dirty (modified/added/untracked/deleted) paths appear in the output.

Usage:
    # Default: enumerate ALL dirty warehouse paths (PER-202)
    uv run summarize_changes.py --warehouse <path>

    # Opt-in legacy behavior: filter through invoking project's beacon.yaml
    uv run summarize_changes.py --warehouse <path> --only-project-artifacts
    uv run summarize_changes.py --warehouse <path> --only-project-artifacts --project-root <path>
    uv run summarize_changes.py --warehouse <path> --only-project-artifacts --beacon-yaml <path>

beacon.yaml resolution order (only when --only-project-artifacts is set):
  1. --beacon-yaml (explicit path) takes highest precedence.
  2. --project-root / auto-detected project root → <project_root>/.agentic-beacon/beacon.yaml.
  3. If neither is discoverable, exits non-zero with a clear message.
"""

import argparse
import glob
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

# ─────────────────────────────────────────────────────────────────────────────
# Inline tracked-paths helper (replaces beacon.domains.warehouse._tracked_paths)
# ─────────────────────────────────────────────────────────────────────────────


def _git_tracked_or_staged_deleted(warehouse_path: Path, pathspec: str) -> set[str]:
    """Return tracked paths matching pathspec, INCLUDING staged-for-deletion ones."""
    found = set()
    rc, stdout, _ = _run_git(warehouse_path, ["ls-files", "--", pathspec])
    if rc == 0:
        for line in stdout.strip().splitlines():
            if line and ".git" not in Path(line).parts:
                found.add(line)
    rc, stdout, _ = _run_git(
        warehouse_path,
        ["diff", "--cached", "--name-only", "--diff-filter=D", "--", pathspec],
    )
    if rc == 0:
        for line in stdout.strip().splitlines():
            if line and ".git" not in Path(line).parts:
                found.add(line)
    return found


def _expand_pattern(warehouse_path: Path, pattern: str) -> list[str]:
    """Expand a beacon.yaml pattern to concrete relative paths."""
    if "*" in pattern or "?" in pattern:
        # Glob finds existing files (including untracked)
        matches = glob.glob(str(warehouse_path / pattern), recursive=True)
        paths = {
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
            and ".git" not in Path(m).relative_to(warehouse_path).parts
        }
        # Supplement with tracked files, including staged deletions
        paths |= _git_tracked_or_staged_deleted(warehouse_path, pattern)
        return sorted(paths)

    p = warehouse_path / pattern
    # Treat as directory pattern if it ends with '/' OR the path exists as a dir.
    # The '/' suffix is the beacon.yaml convention for directories; we must also
    # handle the case where git rm has removed an empty directory from disk.
    if pattern.endswith("/") or p.is_dir():
        matches = glob.glob(str(p / "**" / "*"), recursive=True) if p.exists() else []
        paths = {
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
            and ".git" not in Path(m).relative_to(warehouse_path).parts
        }
        # Supplement with tracked files, including staged deletions
        paths |= _git_tracked_or_staged_deleted(warehouse_path, pattern)
        return sorted(paths)

    if p.is_file():
        return [pattern]

    return [pattern]


def get_tracked_paths(warehouse: Path, beacon_yaml: Path) -> list[str]:
    """Return beacon.yaml-tracked paths relative to warehouse root.

    Parses beacon.yaml with yaml.safe_load — no beacon package required.
    Handles missing artifacts, missing skills/contexts sub-lists gracefully.
    """
    if not beacon_yaml.exists():
        return []

    raw = yaml.safe_load(beacon_yaml.read_text()) or {}
    artifacts = raw.get("artifacts") or {}
    skills_patterns: list[str] = artifacts.get("skills") or []
    contexts_patterns: list[str] = artifacts.get("contexts") or []
    agents_patterns: list[str] = artifacts.get("agents") or []

    paths: list[str] = []
    # Walk all three artifact types: skills, contexts, agents.
    # Matches beacon.core.manifest.beacon.ArtifactsConfig (extra=forbid).
    # Knowledge files are intentionally NOT walked here — they auto-derive
    # during abc sync / abc adopt from context+skill references.
    for pattern in skills_patterns:
        paths.extend(_expand_pattern(warehouse, pattern))
    for pattern in contexts_patterns:
        paths.extend(_expand_pattern(warehouse, pattern))
    for pattern in agents_patterns:
        paths.extend(_expand_pattern(warehouse, pattern))
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# Project-root detection
# ─────────────────────────────────────────────────────────────────────────────


def _find_project_root(start: Path) -> Path | None:
    """Walk up from *start* looking for .agentic-beacon/config.toml.

    Returns the directory containing .agentic-beacon/config.toml, or None if
    not found before reaching the filesystem root.
    """
    current = start.resolve()
    for path in [current, *current.parents]:
        if (path / ".agentic-beacon" / "config.toml").exists():
            return path
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Git helpers
# ─────────────────────────────────────────────────────────────────────────────


def _run_git(
    warehouse: Path, args: list[str], timeout: int = 30
) -> tuple[int, str, str]:
    """Run a git command inside warehouse, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", "-C", str(warehouse)] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def get_git_status(warehouse: Path, path: str) -> str:
    """Return porcelain status code for a single tracked path (e.g. ' M', 'A ', '??')."""
    rc, stdout, stderr = _run_git(warehouse, ["status", "--porcelain", "--", path])
    if rc != 0:
        raise RuntimeError(f"git status failed for {path!r}: {stderr.strip()}")
    return stdout[:2] if stdout else ""


def get_diff_stat(warehouse: Path, path: str) -> str:
    """Return one-line diff --stat summary for a path (empty if no diff).

    Falls back to --cached when the unstaged diff exits non-zero OR returns
    empty stdout (the latter covers staged-only changes where the working tree
    matches the index for that path).
    """
    rc, stdout, _ = _run_git(warehouse, ["diff", "--stat", "--", path])
    if rc != 0 or not stdout.strip():
        # Either git failed, or unstaged diff is empty — try staged.
        rc2, stdout2, _ = _run_git(
            warehouse, ["diff", "--cached", "--stat", "--", path]
        )
        if rc2 != 0:
            return ""
        if stdout2.strip():
            stdout = stdout2
        elif not stdout.strip():
            return ""

    # Extract the summary line (last non-empty line)
    lines = [line.strip() for line in stdout.strip().splitlines() if line.strip()]
    if not lines:
        return ""
    # The stat summary looks like "1 file changed, 2 insertions(+)"
    return lines[-1]


def get_last_commit_age_days(warehouse: Path, path: str) -> int | None:
    """Return days since the file's last commit, or None if never committed."""
    rc, stdout, _ = _run_git(warehouse, ["log", "-1", "--format=%cI", "--", path])
    if rc != 0 or not stdout.strip():
        return None

    date_str = stdout.strip()
    if not date_str:
        return None

    try:
        commit_dt = datetime.fromisoformat(date_str)
        # Ensure timezone-aware comparison
        now = datetime.now(tz=UTC)
        if commit_dt.tzinfo is None:
            commit_dt = commit_dt.replace(tzinfo=UTC)
        delta = now - commit_dt
        return max(0, delta.days)
    except ValueError:
        return None


def is_dirty(status_code: str) -> bool:
    """Return True if the status code indicates a dirty (non-clean) file."""
    if not status_code:
        return False
    # Porcelain codes: '??' = untracked, 'M ' or ' M' = modified, 'A ' = added, etc.
    # A completely clean file returns an empty porcelain line.
    stripped = status_code.strip()
    return bool(stripped)


# ─────────────────────────────────────────────────────────────────────────────
# Warehouse-wide enumeration (PER-202 default)
# ─────────────────────────────────────────────────────────────────────────────


_AREA_PREFIXES = ("contexts", "knowledge", "skills", "agents")


def classify_warehouse_area(path: str) -> str:
    """Return the warehouse area for `path` ('contexts'/'knowledge'/'skills'/'agents'/'other').

    Top-level directory of the warehouse-relative path determines the area.
    """
    head = path.split("/", 1)[0] if path else ""
    return head if head in _AREA_PREFIXES else "other"


def enumerate_dirty_paths(warehouse: Path) -> list[tuple[str, str]]:
    """Return [(path, status_code)] for every dirty path in the warehouse working tree.

    Uses `git status --porcelain=v1 -z` so the parser is immune to:
      * substring collisions on ` -> ` in regular filenames
      * git's C-style quoting of paths containing spaces or special chars
      * rename source paths that themselves contain ` -> `

    The `-z` format emits NUL-delimited records with no escaping. A normal
    entry is one record `XY <path>\\0`; rename / copy entries occupy two
    records `XY <new>\\0<old>\\0`. We report the destination path for
    rename/copy entries (the same convention as the human-readable format).

    `--untracked-files=all` is required so a brand-new directory (e.g.
    `skills/never-adopted/`) expands to its constituent files rather than
    appearing as a single directory entry.
    """
    rc, stdout_bytes, stderr_bytes = _run_git_bytes(
        warehouse, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]
    )
    if rc != 0:
        raise RuntimeError(
            f"git status failed in {warehouse}: "
            f"{stderr_bytes.decode('utf-8', errors='replace').strip()}"
        )

    # Split on NUL; trailing NUL produces an empty final record.
    records = stdout_bytes.split(b"\0")
    if records and records[-1] == b"":
        records.pop()

    entries: list[tuple[str, str]] = []
    i = 0
    while i < len(records):
        rec = records[i]
        if len(rec) < 3:
            i += 1
            continue
        code = rec[:2].decode("utf-8", errors="replace")
        new_path = rec[3:].decode("utf-8", errors="replace")
        if code[0] in ("R", "C") and i + 1 < len(records):
            # Rename/copy: also consume the old-path record.
            i += 2
        else:
            i += 1
        if ".git" in Path(new_path).parts:
            continue
        entries.append((new_path, code))
    return entries


def _run_git_bytes(
    warehouse: Path, args: list[str], timeout: int = 30
) -> tuple[int, bytes, bytes]:
    """Run a git command inside warehouse, return (rc, stdout_bytes, stderr_bytes)."""
    result = subprocess.run(
        ["git", "-C", str(warehouse)] + args,
        capture_output=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def summarize_all(warehouse: Path) -> dict:
    """Build the summary dict of every dirty path in the warehouse working tree."""
    try:
        entries = enumerate_dirty_paths(warehouse)
    except Exception as e:
        print(f"Error enumerating dirty paths: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for path, status in sorted(entries, key=lambda e: e[0]):
        diff_stat = get_diff_stat(warehouse, path)
        age = get_last_commit_age_days(warehouse, path)
        results.append(
            {
                "path": path,
                "git_status": status,
                "diff_stat": diff_stat,
                "last_commit_age_days": age,
                "warehouse_area": classify_warehouse_area(path),
            }
        )

    return {"tracked_paths": results}


# ─────────────────────────────────────────────────────────────────────────────
# beacon.yaml-filtered enumeration (--only-project-artifacts opt-in)
# ─────────────────────────────────────────────────────────────────────────────


def summarize(warehouse: Path, beacon_yaml: Path) -> dict:
    """Build the summary dict of dirty paths filtered through beacon.yaml.

    Used by `--only-project-artifacts`. Returns the same JSON shape as
    `summarize_all`, including `warehouse_area`.
    """
    if not beacon_yaml.exists():
        return {"tracked_paths": []}

    try:
        tracked = get_tracked_paths(warehouse, beacon_yaml)
    except Exception as e:
        print(f"Error enumerating tracked paths: {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for path in sorted(tracked):
        try:
            status = get_git_status(warehouse, path)
        except RuntimeError as e:
            print(f"Warning: {e}", file=sys.stderr)
            continue

        if not is_dirty(status):
            # Clean file — skip
            continue

        diff_stat = get_diff_stat(warehouse, path)
        age = get_last_commit_age_days(warehouse, path)

        results.append(
            {
                "path": path,
                "git_status": status,
                "diff_stat": diff_stat,
                "last_commit_age_days": age,
                "warehouse_area": classify_warehouse_area(path),
            }
        )

    return {"tracked_paths": results}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize dirty warehouse paths as JSON."
    )
    parser.add_argument(
        "--warehouse",
        required=True,
        help="Absolute path to the warehouse root.",
    )
    parser.add_argument(
        "--only-project-artifacts",
        action="store_true",
        help=(
            "Restore legacy behavior: filter dirty paths through the invoking "
            "project's beacon.yaml. Requires --beacon-yaml or a resolvable "
            "project root."
        ),
    )
    parser.add_argument(
        "--beacon-yaml",
        default=None,
        help=(
            "Explicit path to beacon.yaml. Only honored with --only-project-artifacts. "
            "Takes precedence over --project-root and auto-detection."
        ),
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help=(
            "Path to the project root (the directory containing .agentic-beacon/). "
            "Only honored with --only-project-artifacts. When omitted, "
            "auto-detected by walking up from the current directory."
        ),
    )
    args = parser.parse_args()

    warehouse = Path(args.warehouse)
    if not warehouse.is_dir():
        print(f"Error: warehouse path does not exist: {warehouse}", file=sys.stderr)
        sys.exit(1)

    # Default (PER-202): enumerate ALL dirty warehouse paths, no project context.
    if not args.only_project_artifacts:
        try:
            result = summarize_all(warehouse)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Opt-in legacy: filter through invoking project's beacon.yaml.
    if args.beacon_yaml:
        beacon_yaml = Path(args.beacon_yaml)
    else:
        if args.project_root:
            project_root = Path(args.project_root)
        else:
            project_root = _find_project_root(Path.cwd())

        if project_root is None:
            print(
                "Error: --only-project-artifacts requires a resolvable project root "
                "(.agentic-beacon/config.toml not found in current directory or any parent). "
                "Pass --project-root <path> or --beacon-yaml <path> explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

        beacon_yaml = project_root / ".agentic-beacon" / "beacon.yaml"

    try:
        result = summarize(warehouse, beacon_yaml)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
