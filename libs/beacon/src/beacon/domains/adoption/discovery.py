"""Artifact discovery and classification for the abc adopt command.

Provides:
- classify_artifact_type(): map warehouse-relative paths to artifact types
- find_knowledge_node_for_file(): locate knowledge nodes from file paths
- list_knowledge_nodes(): scan warehouse for all knowledge nodes
- discover_adoptable(): full-scan discovery with recent-commit annotation
- count_unadopted_since(): lightweight count for sync notification
- is_adopted(): check whether a path is already declared in beacon.yaml
- build_candidates(): construct AdoptCandidate lists from file paths
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from beacon.domains.adoption.models import (
    ADOPTABLE_TYPES,
    NEW_TAG_MAX_COMMITS,
    AdoptCandidate,
)

if TYPE_CHECKING:
    from beacon.core.manifest.beacon import BeaconManifest


# ─────────────────────────────────────────────────────────────
# Classification helpers
# ─────────────────────────────────────────────────────────────


def classify_artifact_type(path: str) -> str | None:
    """Return artifact_type for a warehouse-relative path, or None if not adoptable."""
    for atype in ADOPTABLE_TYPES:
        if path.startswith(atype + "/"):
            return atype
    return None


def skill_dir_from_path(path: str) -> str:
    """Convert any file under a skill dir to the directory form with trailing slash.

    E.g. "skills/foo/SKILL.md" → "skills/foo/"
    """
    parts = path.split("/")
    if len(parts) >= 2:
        return f"skills/{parts[1]}/"
    return path


# ─────────────────────────────────────────────────────────────
# Adoption state helpers
# ─────────────────────────────────────────────────────────────


def adoption_target_dirs() -> list[Path]:
    """Return candidate global agent directories for all supported tools."""
    return [
        Path.home() / ".config" / "opencode" / "agents",
        Path.home() / ".claude" / "agents",
    ]


def is_agent_installed(agent_path: str) -> bool:
    """Return True if the warehouse agent is installed in any global agent directory."""
    filename = Path(agent_path).name
    return any((d / filename).exists() for d in adoption_target_dirs())


def is_adopted(path: str, beacon_settings: BeaconManifest) -> bool:
    """Return True if path is already declared in beacon.yaml.

    Handles exact matches and glob patterns (e.g. ``knowledge/**/*.md``).
    Skill directory paths are matched with and without trailing slash.
    """
    normalized = path.rstrip("/")
    all_beacon = (
        beacon_settings.artifacts.contexts
        + beacon_settings.artifacts.skills
        + beacon_settings.artifacts.agents
    )
    for bp in all_beacon:
        bp_norm = bp.rstrip("/")
        if bp_norm == normalized:
            return True
        if fnmatch.fnmatch(normalized, bp_norm):
            return True
    return False


# ─────────────────────────────────────────────────────────────
# Description extraction
# ─────────────────────────────────────────────────────────────


def extract_skill_description(content: str) -> str:
    """Extract description from SKILL.md YAML frontmatter or markdown bold syntax."""
    if content.startswith("---"):
        try:
            end = content.index("---", 3)
            for line in content[3:end].splitlines():
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip()
        except ValueError:
            pass
    # Fallback: **description:** text
    match = re.search(r"\*\*description:\*\*\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return ""


def extract_heading_description(content: str) -> str:
    """Extract the first # Heading from markdown content."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def extract_description(warehouse_path: Path, candidate_path: str) -> str:
    """Extract a human-readable description from a warehouse artifact."""
    artifact_type = classify_artifact_type(candidate_path)
    if artifact_type == "skills":
        parts = candidate_path.split("/")
        if len(parts) >= 2:
            skill_md = warehouse_path / "skills" / parts[1] / "SKILL.md"
            if skill_md.exists():
                return extract_skill_description(skill_md.read_text(encoding="utf-8"))
    else:
        file_path = warehouse_path / candidate_path
        if file_path.exists():
            return extract_heading_description(file_path.read_text(encoding="utf-8"))
    return ""


# ─────────────────────────────────────────────────────────────
# Git helpers
# ─────────────────────────────────────────────────────────────


def run_git_diff(warehouse_path: Path, old_sha: str, diff_filter: str) -> list[str]:
    """Run git diff --name-only with the given filter and return file paths."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(warehouse_path),
                "diff",
                "--name-only",
                f"--diff-filter={diff_filter}",
                f"{old_sha}..HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [p for p in result.stdout.strip().splitlines() if p]


def build_new_file_commits_map(
    warehouse_path: Path,
    max_commits: int = NEW_TAG_MAX_COMMITS,
) -> dict[str, int]:
    """Return {file_path: commits_ago} for files first added in the last max_commits commits.

    commits_ago is 1-indexed: 1 = added in HEAD, 2 = added in HEAD~1, etc.
    Returns empty dict if git is unavailable or no added files found.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(warehouse_path),
                "log",
                f"-{max_commits}",
                "--diff-filter=A",
                "--name-only",
                "--pretty=format:BEACON_COMMIT_MARKER",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}

    file_map: dict[str, int] = {}
    commit_index = 0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped == "BEACON_COMMIT_MARKER":
            commit_index += 1
        elif stripped and commit_index > 0:
            if stripped not in file_map:
                file_map[stripped] = commit_index
    return file_map


def annotate_with_commits_ago(
    candidates: list[AdoptCandidate],
    warehouse_path: Path,
) -> None:
    """Set commits_ago on candidates added within NEW_TAG_MAX_COMMITS commits of HEAD."""
    file_map = build_new_file_commits_map(warehouse_path)
    if not file_map:
        return
    for candidate in candidates:
        prefix = candidate.path.rstrip("/")
        min_n: int | None = None
        for file_path, n in file_map.items():
            if file_path == prefix or file_path.startswith(prefix + "/"):
                if min_n is None or n < min_n:
                    min_n = n
        if min_n is not None:
            candidate.commits_ago = min_n


# ─────────────────────────────────────────────────────────────
# Candidate building
# ─────────────────────────────────────────────────────────────


def build_candidates(
    warehouse_path: Path,
    paths: list[str],
    beacon_settings: BeaconManifest,
    *,
    is_new: bool,
) -> list[AdoptCandidate]:
    """Build AdoptCandidate list from a list of warehouse-relative file paths.

    Skills are grouped by directory.
    """
    seen_skill_dirs: set[str] = set()
    candidates: list[AdoptCandidate] = []

    for path in paths:
        artifact_type = classify_artifact_type(path)
        if artifact_type is None:
            continue

        if artifact_type == "skills":
            skill_dir = skill_dir_from_path(path)
            skill_key = skill_dir.rstrip("/")
            if skill_key in seen_skill_dirs:
                continue
            if is_adopted(skill_dir, beacon_settings):
                continue
            seen_skill_dirs.add(skill_key)
            skill_md = (
                warehouse_path / "skills" / skill_key.split("/", 1)[-1] / "SKILL.md"
            )
            desc = (
                extract_skill_description(skill_md.read_text(encoding="utf-8"))
                if skill_md.exists()
                else ""
            )
            candidates.append(
                AdoptCandidate(
                    artifact_type="skills",
                    path=skill_dir,
                    description=desc,
                    is_new=is_new,
                )
            )
        else:
            if is_adopted(path, beacon_settings):
                continue
            desc = extract_description(warehouse_path, path)
            candidates.append(
                AdoptCandidate(
                    artifact_type=artifact_type,
                    path=path,
                    description=desc,
                    is_new=is_new,
                )
            )

    return candidates


def discover_all(
    warehouse_path: Path,
    beacon_settings: BeaconManifest,
) -> list[AdoptCandidate]:
    """Full-scan mode: return every warehouse artifact not in beacon.yaml."""
    from beacon.domains.distribution.distributor import WarehouseDistributor

    distributor = WarehouseDistributor(
        warehouse_root=warehouse_path,
        target_root=warehouse_path,  # target_root unused here
    )
    available = distributor.list_available()

    candidates: list[AdoptCandidate] = []

    # Contexts — list_available returns paths like "contexts/foo.md"
    for ctx_path in available.get("contexts", []):
        if not is_adopted(ctx_path, beacon_settings):
            desc = extract_description(warehouse_path, ctx_path)
            candidates.append(
                AdoptCandidate(
                    artifact_type="contexts",
                    path=ctx_path,
                    description=desc,
                    is_new=False,
                )
            )

    # Skills — list_available returns skill names like "example-skill"
    for skill_name in available.get("skills", []):
        skill_path = f"skills/{skill_name}/"
        if not is_adopted(skill_path, beacon_settings):
            skill_md = warehouse_path / "skills" / skill_name / "SKILL.md"
            desc = (
                extract_skill_description(skill_md.read_text(encoding="utf-8"))
                if skill_md.exists()
                else ""
            )
            candidates.append(
                AdoptCandidate(
                    artifact_type="skills",
                    path=skill_path,
                    description=desc,
                    is_new=False,
                )
            )

    # Agents — list_available returns paths like "agents/code-reviewer.md".
    # Per Decision 1, "adopted" for the adopt TUI means "declared in
    # beacon.yaml.artifacts.agents". Global install state is a side effect of
    # ticking — not the source of truth for project membership. Filtering on
    # global state would hide globally-installed agents from existing users
    # running `abc adopt` post-upgrade to opt into per-project tracking (the
    # migration path documented in design.md Decision 4).
    for agent_path in available.get("agents", []):
        if not is_adopted(agent_path, beacon_settings):
            desc = extract_description(warehouse_path, agent_path)
            candidates.append(
                AdoptCandidate(
                    artifact_type="agents",
                    path=agent_path,
                    description=desc,
                    is_new=False,
                )
            )

    return candidates


# ─────────────────────────────────────────────────────────────
# Public API: discovery
# ─────────────────────────────────────────────────────────────


def discover_adoptable(
    warehouse_path: Path,
    beacon_settings: BeaconManifest,
    sync_sha: str | None = None,
    *,
    show_all: bool = False,
) -> tuple[list[AdoptCandidate], list[str]]:
    """Discover warehouse artifacts available to adopt.

    Always performs a full warehouse scan and annotates candidates with
    commits_ago when they were added within NEW_TAG_MAX_COMMITS commits of HEAD.

    Args:
        warehouse_path: Path to the warehouse root.
        beacon_settings: Parsed beacon.yaml settings.
        sync_sha: Kept for backward compatibility; no longer used for discovery.
        show_all: Kept for backward compatibility; full scan is always used.

    Returns:
        (candidates, updated_adopted_paths) where:
        - candidates: unadopted AdoptCandidates with commits_ago annotated
        - updated_adopted_paths: always empty (retained for API compatibility)
    """
    candidates = discover_all(warehouse_path, beacon_settings)
    annotate_with_commits_ago(candidates, warehouse_path)
    return candidates, []


def count_unadopted_since(
    warehouse_path: Path,
    beacon_settings: BeaconManifest,
    sync_sha: str,
) -> int:
    """Lightweight count of new warehouse artifacts since sync_sha not in beacon.yaml.

    Uses only git diff + path comparison — no file reads for descriptions.
    """
    new_paths = run_git_diff(warehouse_path, sync_sha, "A")
    seen_skill_dirs: set[str] = set()
    count = 0

    for path in new_paths:
        artifact_type = classify_artifact_type(path)
        if artifact_type is None or artifact_type == "agents":
            continue
        if artifact_type == "skills":
            skill_dir = skill_dir_from_path(path)
            skill_key = skill_dir.rstrip("/")
            if skill_key in seen_skill_dirs:
                continue
            if not is_adopted(skill_dir, beacon_settings):
                seen_skill_dirs.add(skill_key)
                count += 1
        else:
            if not is_adopted(path, beacon_settings):
                count += 1

    return count
