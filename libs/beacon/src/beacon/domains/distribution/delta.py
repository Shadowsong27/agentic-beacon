"""Delta comparison for local artifacts vs warehouse.

This module implements hash-based and diff-based comparison between
local project artifacts and warehouse source files.

For skills, comparison is done against the live agent installation directories
(e.g. .opencode/skills/, .claude/skills/) rather than the artifact snapshot,
because the agent reads from those locations — not from .agentic-beacon/artifacts/.
"""

import hashlib
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from loguru import logger
from pydantic import BaseModel


class DeltaStatus(Enum):
    """Status of a compared artifact."""

    IDENTICAL = "identical"
    MODIFIED = "modified"
    ADDED = "added"  # Exists locally but not in warehouse
    MISSING = "missing"  # In beacon.yaml but not synced locally
    STALE = "stale"  # Historical status retained for compatibility.
    PENDING = "pending"  # Skill file not yet distributed to this agent (not in warehouse, not in agent)


class ComparisonResult(BaseModel):
    """Result of comparing a single artifact."""

    path: str
    status: DeltaStatus
    local_hash: str | None = None
    warehouse_hash: str | None = None
    # For skills: per-agent comparison results {agent_name: DeltaStatus}
    # Empty for non-skill artifacts.
    agent_statuses: dict[str, DeltaStatus] = {}

    model_config = {"arbitrary_types_allowed": True}

    @property
    def is_skill(self) -> bool:
        return bool(self.agent_statuses)


@dataclass
class DeltaSummary:
    """Summary of all artifact comparisons."""

    results: list[ComparisonResult] = field(default_factory=list)

    @property
    def modified(self) -> list[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.MODIFIED]

    @property
    def added(self) -> list[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.ADDED]

    @property
    def missing(self) -> list[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.MISSING]

    @property
    def identical(self) -> list[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.IDENTICAL]

    @property
    def stale(self) -> list[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.STALE]

    @property
    def has_differences(self) -> bool:
        return any(r.status != DeltaStatus.IDENTICAL for r in self.results)


@dataclass
class DeltaComparator:
    """Compares local artifacts against warehouse versions.

    Supports hash-based summary comparison and detailed git diff.
    Only compares artifacts declared in beacon.yaml.

    For skills, comparison is against live agent installation directories
    (skills_paths) rather than the artifact snapshot. This reflects that
    skills are physically copied to agent-specific locations during sync,
    and those are the files agents actually read.

    Args:
        warehouse_path: Path to the warehouse source directory.
        artifacts_path: Path to .agentic-beacon/artifacts/ (used for knowledge/contexts).
        skills_paths: Mapping of agent name to its skills root directory.
            e.g. {"opencode": Path(".opencode/skills"), "claudecode": Path(".claude/skills")}
            If empty, falls back to artifacts_path for skills (backward compat).
    """

    warehouse_path: Path
    artifacts_path: Path
    skills_paths: dict[str, Path] = field(default_factory=dict)
    # agents_paths: mapping of agent name → global agents root dir
    # e.g. {"opencode": Path("~/.config/opencode/agents"), "claudecode": Path("~/.claude/agents")}
    agents_paths: dict[str, Path] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Resolve paths and validate warehouse directory.

        Raises:
            ValueError: If warehouse_path is not a valid directory
        """
        self.warehouse_path = Path(self.warehouse_path).resolve()
        self.artifacts_path = Path(self.artifacts_path).resolve()
        self.skills_paths = {
            agent: Path(p).resolve() for agent, p in self.skills_paths.items()
        }
        logger.debug(
            "DeltaComparator initialized: warehouse={}, artifacts={}, skills_paths={}",
            self.warehouse_path,
            self.artifacts_path,
            self.skills_paths,
        )

        if not self.warehouse_path.is_dir():
            raise ValueError(
                f"Warehouse path is not a valid directory: {self.warehouse_path}"
            )

    def compute_hash(self, file_path: Path | str) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to file to hash

        Returns:
            Hex digest of SHA256 hash

        Raises:
            FileNotFoundError: If file doesn't exist
            IsADirectoryError: If path is a directory
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.is_dir():
            raise IsADirectoryError(f"Expected file, found directory: {file_path}")

        # Resolve symlinks to hash target content
        actual_path = file_path.resolve()

        sha256 = hashlib.sha256()
        with open(actual_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def skill_live_path(self, agent: str, relative_path: str) -> Path:
        """Resolve the live installed path for a skill on a given agent.

        Skills are stored in the warehouse as skills/<name>/SKILL.md but are
        installed into <agent_skills_root>/<name>/SKILL.md.

        Args:
            agent: Agent name key into self.skills_paths.
            relative_path: Warehouse-relative path, e.g. "skills/opsx-enhance/SKILL.md".

        Returns:
            Absolute path to the skill's live location for that agent.
        """
        agent_root = self.skills_paths[agent]
        # Strip the leading "skills/" prefix to get "<name>/SKILL.md"
        parts = Path(relative_path).parts
        if parts[0] == "skills":
            skill_relative = Path(*parts[1:])
        else:
            skill_relative = Path(relative_path)
        return agent_root / skill_relative

    def agent_live_path(self, agent: str, relative_path: str) -> Path:
        """Resolve the global installed path for an agent definition file.

        Agent files are stored in the warehouse as agents/<name>.md and are
        installed into the agent-specific global agents directory.

        Args:
            agent: Agent name key into self.agents_paths ("opencode" or "claudecode").
            relative_path: Warehouse-relative path, e.g. "agents/code-reviewer.md".

        Returns:
            Absolute path to the agent file's global location for that tool.
        """
        parts = Path(relative_path).parts
        if parts[0] == "agents":
            agent_relative = Path(*parts[1:])
        else:
            agent_relative = Path(relative_path)
        return (
            Path.home()
            / (".config/opencode/agents" if agent == "opencode" else ".claude/agents")
            / agent_relative
        )

    def compare_agent_file(self, relative_path: str) -> ComparisonResult:
        """Compare an agent definition file against all global agent directories.

        Returns ComparisonResult with per-agent statuses:
        - ADDED    — file exists globally but not in warehouse (new, never committed)
        - MODIFIED — file exists both globally and in warehouse but differs
        - IDENTICAL — file matches warehouse exactly
        - MISSING  — file is in warehouse but absent from this tool's global dir

        STALE is not returned here; symlinked global agents read warehouse files directly.

        Args:
            relative_path: Warehouse-relative path, e.g. "agents/code-reviewer.md".
        """
        warehouse_file = self.warehouse_path / relative_path
        warehouse_exists = warehouse_file.is_file()
        warehouse_hash = self.compute_hash(warehouse_file) if warehouse_exists else None

        agent_statuses: dict[str, DeltaStatus] = {}

        for agent in self.agents_paths:
            live_file = self.agent_live_path(agent, relative_path)
            live_exists = live_file.is_file()

            if not live_exists:
                agent_statuses[agent] = DeltaStatus.MISSING
            elif not warehouse_exists:
                # File exists globally but has no warehouse counterpart yet
                agent_statuses[agent] = DeltaStatus.ADDED
            else:
                live_hash = self.compute_hash(live_file)
                if live_hash == warehouse_hash:
                    agent_statuses[agent] = DeltaStatus.IDENTICAL
                else:
                    agent_statuses[agent] = DeltaStatus.MODIFIED

        # Aggregate: ADDED > MODIFIED > MISSING > IDENTICAL
        if agent_statuses:
            priority = {
                DeltaStatus.ADDED: 3,
                DeltaStatus.MODIFIED: 2,
                DeltaStatus.MISSING: 1,
                DeltaStatus.IDENTICAL: 0,
            }
            aggregate = max(agent_statuses.values(), key=lambda s: priority.get(s, 0))
        else:
            aggregate = DeltaStatus.MISSING

        return ComparisonResult(
            path=relative_path,
            status=aggregate,
            warehouse_hash=warehouse_hash,
            agent_statuses=agent_statuses,
        )

    def compare_file(self, relative_path: str) -> ComparisonResult:
        """Compare a single artifact between local and warehouse.

        For skills (when skills_paths is configured): compares warehouse against
        each agent's live installation directory and rolls up to a single status.
        For knowledge/contexts: compares warehouse against artifacts_path.

        Args:
            relative_path: Relative path from artifacts/warehouse root

        Returns:
            ComparisonResult with status and hashes
        """
        is_skill = relative_path.startswith("skills/") and bool(self.skills_paths)
        is_agent = relative_path.startswith("agents/")

        if is_skill:
            return self._compare_skill_file(relative_path)

        if is_agent:
            return self.compare_agent_file(relative_path)

        local_file = self.artifacts_path / relative_path
        warehouse_file = self.warehouse_path / relative_path

        local_exists = local_file.is_file()
        warehouse_exists = warehouse_file.is_file()
        logger.debug(
            "Comparing {}: local_exists={}, warehouse_exists={}",
            relative_path,
            local_exists,
            warehouse_exists,
        )

        if not local_exists and not warehouse_exists:
            return ComparisonResult(
                path=relative_path,
                status=DeltaStatus.MISSING,
            )

        if local_exists and not warehouse_exists:
            local_hash = self.compute_hash(local_file)
            return ComparisonResult(
                path=relative_path,
                status=DeltaStatus.ADDED,
                local_hash=local_hash,
            )

        if not local_exists and warehouse_exists:
            warehouse_hash = self.compute_hash(warehouse_file)
            return ComparisonResult(
                path=relative_path,
                status=DeltaStatus.MISSING,
                warehouse_hash=warehouse_hash,
            )

        # Both exist - compare hashes
        local_hash = self.compute_hash(local_file)
        warehouse_hash = self.compute_hash(warehouse_file)

        if local_hash == warehouse_hash:
            return ComparisonResult(
                path=relative_path,
                status=DeltaStatus.IDENTICAL,
                local_hash=local_hash,
                warehouse_hash=warehouse_hash,
            )
        else:
            return ComparisonResult(
                path=relative_path,
                status=DeltaStatus.MODIFIED,
                local_hash=local_hash,
                warehouse_hash=warehouse_hash,
            )

    def _compare_skill_file(self, relative_path: str) -> ComparisonResult:
        """Compare a skill against all live agent installation directories.

        The rolled-up status reflects the worst case across all agents:
        MODIFIED > MISSING > ADDED > IDENTICAL.

        Args:
            relative_path: Warehouse-relative path, e.g. "skills/opsx-enhance/SKILL.md".

        Returns:
            ComparisonResult with per-agent statuses and an aggregate status.
        """
        warehouse_file = self.warehouse_path / relative_path
        warehouse_exists = warehouse_file.is_file()
        warehouse_hash = self.compute_hash(warehouse_file) if warehouse_exists else None

        agent_statuses: dict[str, DeltaStatus] = {}

        for agent, _agent_root in self.skills_paths.items():
            live_file = self.skill_live_path(agent, relative_path)
            live_exists = live_file.is_file()

            if not live_exists and not warehouse_exists:
                agent_statuses[agent] = DeltaStatus.PENDING
            elif live_exists and not warehouse_exists:
                agent_statuses[agent] = DeltaStatus.ADDED
            elif not live_exists and warehouse_exists:
                agent_statuses[agent] = DeltaStatus.MISSING
            else:
                live_hash = self.compute_hash(live_file)
                if live_hash == warehouse_hash:
                    agent_statuses[agent] = DeltaStatus.IDENTICAL
                else:
                    agent_statuses[agent] = DeltaStatus.MODIFIED

        # Roll up: worst status across all agents
        # Priority: MODIFIED > MISSING > ADDED > PENDING > IDENTICAL
        priority = {
            DeltaStatus.MODIFIED: 4,
            DeltaStatus.MISSING: 3,
            DeltaStatus.ADDED: 2,
            DeltaStatus.PENDING: 1,
            DeltaStatus.IDENTICAL: 0,
        }
        aggregate = max(agent_statuses.values(), key=lambda s: priority[s])

        return ComparisonResult(
            path=relative_path,
            status=aggregate,
            warehouse_hash=warehouse_hash,
            agent_statuses=agent_statuses,
        )

    def compare_all(self, artifact_paths: list[str] | None = None) -> DeltaSummary:
        """Compare all artifacts.

        Args:
            artifact_paths: List of relative paths to compare.
                If None, compares all files in artifacts directory plus agents/ if configured.

        Returns:
            DeltaSummary with all comparison results
        """
        summary = DeltaSummary()

        if artifact_paths is not None:
            # Compare only specified paths
            for path in artifact_paths:
                result = self.compare_file(path)
                summary.results.append(result)
        else:
            # Compare all files in artifacts directory
            if self.artifacts_path.exists():
                for file_path in sorted(self.artifacts_path.rglob("*")):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(self.artifacts_path))
                        result = self.compare_file(rel_path)
                        summary.results.append(result)

            # Also iterate agents/ from warehouse when agents_paths is configured
            if self.agents_paths:
                agents_dir = self.warehouse_path / "agents"
                if agents_dir.is_dir():
                    from beacon.domains.distribution.distributor import is_partial_path

                    for agent_file in sorted(agents_dir.rglob("*")):
                        if agent_file.is_file():
                            rel_path = str(agent_file.relative_to(self.warehouse_path))
                            if is_partial_path(rel_path):
                                continue
                            result = self.compare_file(rel_path)
                            summary.results.append(result)

        return summary

    def compare_from_config(self, beacon_settings) -> DeltaSummary:
        """Compare only artifacts listed in beacon.yaml.

        Detects MODIFIED, IDENTICAL, and MISSING files (those in the warehouse)
        as well as ADDED files (those that exist locally but not in the warehouse).

        For skills: compares against live agent installation directories when
        skills_paths is configured. Falls back to artifacts_path otherwise.

        Args:
            beacon_settings: Parsed BeaconManifest object

        Returns:
            DeltaSummary for beacon.yaml artifacts only
        """
        from .sync_engine import SyncEngine

        # Collect all artifact paths, expanding globs
        seen: set[str] = set()
        artifact_paths: list[str] = []
        sync_engine = SyncEngine(
            warehouse_path=self.warehouse_path,
            artifacts_path=self.artifacts_path,
        )

        for artifact_type in ["skills", "contexts"]:
            patterns = getattr(beacon_settings.artifacts, artifact_type)
            for pattern in patterns:
                if "*" in pattern or "?" in pattern or "[" in pattern:
                    # Glob the warehouse — finds MODIFIED/IDENTICAL/MISSING candidates
                    for rel_path in sync_engine.expand_glob(pattern):
                        if rel_path not in seen:
                            seen.add(rel_path)
                            artifact_paths.append(rel_path)

                    # For skills with live agent paths: glob the agent dirs to catch
                    # ADDED files that only exist locally.
                    # For skills without agent paths (no agents detected): fall back
                    # to artifacts_path glob (backward compat).
                    # For non-skills: glob local artifacts dir.
                    if artifact_type == "skills" and self.skills_paths:
                        for _agent, agent_root in self.skills_paths.items():
                            if agent_root.exists():
                                # Translate pattern: "skills/**/*" → "**/*" relative to agent root
                                parts = Path(pattern).parts
                                if parts[0] == "skills":
                                    agent_pattern = (
                                        str(Path(*parts[1:]))
                                        if len(parts) > 1
                                        else "**/*"
                                    )
                                else:
                                    agent_pattern = pattern
                                for match in agent_root.glob(agent_pattern):
                                    if match.is_file():
                                        skill_rel = match.relative_to(agent_root)
                                        rel_path = str(Path("skills") / skill_rel)
                                        if rel_path not in seen:
                                            seen.add(rel_path)
                                            artifact_paths.append(rel_path)
                    elif self.artifacts_path.exists():
                        for match in self.artifacts_path.glob(pattern):
                            if match.is_file():
                                rel_path = str(match.relative_to(self.artifacts_path))
                                if rel_path not in seen:
                                    seen.add(rel_path)
                                    artifact_paths.append(rel_path)
                else:
                    if artifact_type == "skills":
                        # Normalize to directory form (handles old SKILL.md entries
                        # and new directory entries) without importing from cli.py.
                        p = Path(pattern.rstrip("/"))
                        if p.suffix:  # file-level entry — strip filename
                            p = p.parent
                        if not p.parts or p.parts[0] != "skills":
                            p = Path("skills") / p
                        skill_dir_entry = str(p)
                        skill_name = p.name

                        # Expand files from warehouse
                        for rel_path in sync_engine.expand_glob(
                            f"{skill_dir_entry}/**/*"
                        ):
                            if rel_path not in seen:
                                seen.add(rel_path)
                                artifact_paths.append(rel_path)

                        # Also scan live agent dirs to detect ADDED files
                        if self.skills_paths:
                            for _agent, agent_root in self.skills_paths.items():
                                agent_skill_dir = agent_root / skill_name
                                if agent_skill_dir.exists():
                                    for f in agent_skill_dir.rglob("*"):
                                        if f.is_file():
                                            rel_path = str(
                                                Path("skills")
                                                / skill_name
                                                / f.relative_to(agent_skill_dir)
                                            )
                                            if rel_path not in seen:
                                                seen.add(rel_path)
                                                artifact_paths.append(rel_path)
                    else:
                        if pattern not in seen:
                            seen.add(pattern)
                            artifact_paths.append(pattern)

        return self.compare_all(artifact_paths)

    def detailed_diff(self, relative_path: str, color: bool = True) -> str:
        """Get detailed line-by-line diff using git diff --no-index.

        For skills with agent paths configured: produces a labelled diff section
        for each agent that has the skill installed.  If multiple agents have
        diverged differently from the warehouse, each is shown separately.
        Falls back to the artifact snapshot when no agent has the skill installed.

        For knowledge/contexts: diffs against artifacts_path.

        Args:
            relative_path: Relative path of the artifact to diff
            color: Whether to include ANSI color codes

        Returns:
            Unified diff string, or error message string if files unavailable
        """
        warehouse_file = self.warehouse_path / relative_path

        is_skill = relative_path.startswith("skills/") and bool(self.skills_paths)
        if is_skill:
            # Produce a diff section for every agent that has the skill installed
            sections = []
            for agent in self.skills_paths:
                candidate = self.skill_live_path(agent, relative_path)
                if candidate.exists():
                    if not warehouse_file.exists():
                        sections.append(
                            f"--- {agent} ---\nWarehouse file not found: {relative_path}"
                        )
                    else:
                        diff = self._diff_files(warehouse_file, candidate, color)
                        sections.append(
                            f"--- {agent} ---\n{diff}"
                            if diff
                            else f"--- {agent} ---\n(identical)"
                        )
            if sections:
                return "\n".join(sections)
            # No agent has it installed — fall back to artifact snapshot
            local_file = self.artifacts_path / relative_path
        else:
            local_file = self.artifacts_path / relative_path

        if not local_file.exists():
            return f"Local file not found: {relative_path}"

        if not warehouse_file.exists():
            return f"Warehouse file not found: {relative_path}"

        return self._diff_files(warehouse_file, local_file, color)

    def _diff_files(self, warehouse_file: Path, local_file: Path, color: bool) -> str:
        """Run git diff --no-index between two files and return the output."""
        cmd = ["git", "diff", "--no-index"]
        if color:
            cmd.append("--color=always")
        else:
            cmd.append("--color=never")
        cmd.extend([str(warehouse_file), str(local_file)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            # git diff --no-index returns 0 for identical, 1 for different
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback if git is not available
            return self._simple_diff(warehouse_file, local_file)

    def _simple_diff(self, file1: Path, file2: Path) -> str:
        """Simple line-by-line diff fallback when git is not available."""
        import difflib

        try:
            lines1 = file1.read_text().splitlines()
            lines2 = file2.read_text().splitlines()
        except OSError as e:
            logger.debug("Error reading files for diff: {}", e)
            return f"Error reading files: {e}"

        diff = difflib.unified_diff(
            lines1,
            lines2,
            fromfile=f"warehouse/{file1.name}",
            tofile=f"local/{file2.name}",
            lineterm="",
        )
        return "\n".join(diff)


def enrich_tracked_stale(
    summary: DeltaSummary,
    *,
    warehouse_path: Path,
    artifacts_path: Path,
    comparator: DeltaComparator,
) -> DeltaSummary:
    """No-op in symlink-based model.

    The STALE concept (local file matches last sync SHA but warehouse has
    advanced) does not apply when artifacts are symlinks to the warehouse
    working tree.  Retained for API compatibility.
    """
    return summary
