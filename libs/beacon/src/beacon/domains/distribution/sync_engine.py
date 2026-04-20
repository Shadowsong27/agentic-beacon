"""Sync engine for snapshot-based artifact copying.

This module implements pure copy (no symlinks) syncing of artifacts
from warehouse to project's .agentic-beacon/artifacts/ directory.
"""

import hashlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel


class SyncResult(BaseModel):
    """Result of a sync operation."""

    success: bool
    action: Literal["copied", "skipped", "preserved", "error"]
    source_path: Path | None = None
    dest_path: Path | None = None
    error_message: str | None = None

    model_config = {"arbitrary_types_allowed": True}


class OrphanInfo(BaseModel):
    """Information about a single orphaned artifact file."""

    rel_path: str
    """Relative path under artifacts_path."""

    is_modified: bool
    """True if local content differs from the warehouse copy."""

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class SyncSummary:
    """Summary of a full sync operation."""

    copied: int = 0
    skipped: int = 0
    preserved: int = 0
    pruned: int = 0
    errors: int = 0
    failed_files: list[tuple[str, str]] = field(default_factory=list)
    results: list[SyncResult] = field(default_factory=list)
    log_messages: list[str] = field(default_factory=list)
    pruned_paths: list[str] = field(default_factory=list)


@dataclass
class SyncEngine:
    """Engine for syncing artifacts from warehouse to project.

    Implements snapshot-based pure copy model:
    - No symlinks (for agent compatibility)
    - Idempotent (skips unchanged files)
    - Preserves directory structure
    - Supports glob patterns
    - Supports --preserve (skip locally modified files)
    - Supports --prune (remove artifacts not in beacon.yaml)
    - Supports verbose logging
    """

    warehouse_path: Path
    artifacts_path: Path

    def __post_init__(self) -> None:
        """Normalize paths and ensure artifacts directory exists."""
        self.warehouse_path = Path(self.warehouse_path)
        self.artifacts_path = Path(self.artifacts_path)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        logger.debug(
            "SyncEngine initialized: warehouse={}, artifacts={}",
            self.warehouse_path,
            self.artifacts_path,
        )

    def copy_file(self, relative_path: str, preserve: bool = False) -> SyncResult:
        """Copy a single file from warehouse to artifacts directory.

        Args:
            relative_path: Relative path from warehouse root (e.g., "knowledge/doc.md")
            preserve: If True, skip files with local modifications

        Returns:
            SyncResult indicating success/failure and action taken
        """
        source_file = self.warehouse_path / relative_path
        dest_file = self.artifacts_path / relative_path

        # Check if source exists
        if not source_file.exists():
            logger.debug("Source file not found: {}", source_file)
            return SyncResult(
                success=False,
                action="error",
                source_path=source_file,
                error_message=f"Source file not found: {source_file}",
            )

        # Check if destination exists and is unchanged (idempotent check)
        if dest_file.exists():
            if self._files_identical(source_file, dest_file):
                logger.debug("Skipping unchanged file: {}", relative_path)
                return SyncResult(
                    success=True,
                    action="skipped",
                    source_path=source_file,
                    dest_path=dest_file,
                )

            # File differs - check preserve flag
            if preserve:
                logger.debug("Preserving locally modified file: {}", relative_path)
                return SyncResult(
                    success=True,
                    action="preserved",
                    source_path=source_file,
                    dest_path=dest_file,
                )

        # Create parent directories and copy file
        try:
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (always as regular file, never as symlink)
            if source_file.is_symlink():
                # If source is symlink, copy the target content
                shutil.copy2(source_file.resolve(), dest_file)
            else:
                shutil.copy2(source_file, dest_file)

            logger.debug("Copied: {} -> {}", source_file, dest_file)
            return SyncResult(
                success=True,
                action="copied",
                source_path=source_file,
                dest_path=dest_file,
            )
        except PermissionError as e:
            logger.debug("Permission denied copying {}: {}", relative_path, e)
            return SyncResult(
                success=False,
                action="error",
                source_path=source_file,
                error_message=f"Permission denied: {e}",
            )
        except OSError as e:
            logger.debug("OS error copying {}: {}", relative_path, e)
            return SyncResult(
                success=False,
                action="error",
                source_path=source_file,
                error_message=str(e),
            )

    def _check_file_action(self, relative_path: str, preserve: bool = False) -> str:
        """Determine what action would be taken for a file without copying.

        Args:
            relative_path: Relative path from warehouse root
            preserve: Whether preserve flag is set

        Returns:
            One of "copied", "skipped", "preserved", or "error"
        """
        source_file = self.warehouse_path / relative_path
        dest_file = self.artifacts_path / relative_path

        if not source_file.exists():
            return "error"

        if dest_file.exists():
            if self._files_identical(source_file, dest_file):
                return "skipped"
            if preserve:
                return "preserved"

        return "copied"

    def classify_orphans(self, artifact_paths: list[str]) -> list[OrphanInfo]:
        """Classify files in artifacts_path that are not in artifact_paths.

        A file is an *orphan* if it exists under artifacts_path but is not
        listed in artifact_paths.  Orphans are split into two categories:

        - Prune candidates: the file also exists in the warehouse (was synced
          at some point, then removed from beacon.yaml).  These should be
          deleted after user confirmation.
        - New contributions: the file does NOT exist in the warehouse (was
          created locally and has never been pushed).  These must never be
          auto-deleted.

        Only prune candidates are returned; new contributions are silently
        ignored.

        Args:
            artifact_paths: List of relative paths currently in beacon.yaml.

        Returns:
            List of OrphanInfo for prune candidates, each carrying whether the
            local copy has been modified relative to the warehouse version.
        """
        if not self.artifacts_path.exists():
            return []

        synced_set = set(artifact_paths)
        orphans: list[OrphanInfo] = []

        for file_path in sorted(self.artifacts_path.rglob("*")):
            if not file_path.is_file():
                continue
            rel_path = str(file_path.relative_to(self.artifacts_path))
            if rel_path in synced_set:
                continue

            warehouse_copy = self.warehouse_path / rel_path
            if not warehouse_copy.exists():
                # New contribution — never prune
                logger.debug(
                    "Skipping new contribution (not in warehouse): {}", rel_path
                )
                continue

            is_modified = not self.files_identical(file_path, warehouse_copy)
            orphans.append(OrphanInfo(rel_path=rel_path, is_modified=is_modified))

        return orphans

    def sync_all(
        self,
        artifact_paths: list[str],
        preserve: bool = False,
        prune: bool = False,
        paths_to_prune: list[str] | None = None,
        verbose: bool = False,
        dry_run: bool = False,
        log_fn: Callable[[str], None] | None = None,
    ) -> SyncSummary:
        """Sync all artifacts from a list of paths.

        Args:
            artifact_paths: List of relative paths to sync
            preserve: If True, skip locally modified files
            prune: If True, remove artifacts not in the list (legacy flag —
                   prefer passing paths_to_prune explicitly for confirmed lists)
            paths_to_prune: Explicit list of relative paths to delete.  When
                provided this takes precedence over the automatic prune scan
                driven by ``prune=True``.
            verbose: If True, log detailed operations
            dry_run: If True, preview actions without copying or pruning
            log_fn: Optional callback for log messages

        Returns:
            SyncSummary with operation counts and details
        """
        summary = SyncSummary()

        def log(msg: str) -> None:
            summary.log_messages.append(msg)
            if log_fn:
                log_fn(msg)

        # Sync each artifact
        for path in artifact_paths:
            if verbose or dry_run:
                log(f"Syncing: {path}")

            if dry_run:
                action = self._check_file_action(path, preserve=preserve)
                result = SyncResult(
                    success=action != "error",
                    action=action,  # type: ignore[arg-type]
                )
            else:
                result = self.copy_file(path, preserve=preserve)
            summary.results.append(result)

            if result.action == "copied":
                summary.copied += 1
                if verbose or dry_run:
                    log(f"  {'Would copy' if dry_run else 'Copied'}: {path}")
            elif result.action == "skipped":
                summary.skipped += 1
                if verbose or dry_run:
                    log(f"  Unchanged: {path}")
            elif result.action == "preserved":
                summary.preserved += 1
                if verbose or dry_run:
                    log(
                        f"  {'Would preserve' if dry_run else 'Preserved'} (local changes): {path}"
                    )
            elif result.action == "error":
                summary.errors += 1
                summary.failed_files.append(
                    (path, result.error_message or "unknown error")
                )
                log(f"  Error: {path} - {result.error_message}")

        # Determine which paths to prune
        if paths_to_prune is not None:
            prune_list = paths_to_prune
        elif prune and self.artifacts_path.exists():
            synced_set = set(artifact_paths)
            prune_list = [
                str(f.relative_to(self.artifacts_path))
                for f in sorted(self.artifacts_path.rglob("*"))
                if f.is_file()
                and str(f.relative_to(self.artifacts_path)) not in synced_set
            ]
        else:
            prune_list = []

        for rel_path in prune_list:
            file_path = self.artifacts_path / rel_path
            if dry_run:
                summary.pruned += 1
                summary.pruned_paths.append(rel_path)
                logger.debug("Would prune: {}", rel_path)
                if verbose or dry_run:
                    log(f"  Would prune: {rel_path}")
            else:
                try:
                    file_path.unlink(missing_ok=True)
                    summary.pruned += 1
                    summary.pruned_paths.append(rel_path)
                    logger.debug("Pruned: {}", rel_path)
                    if verbose:
                        log(f"  Pruned: {rel_path}")
                except OSError as e:
                    summary.errors += 1
                    summary.failed_files.append((rel_path, str(e)))
                    log(f"  Error pruning {rel_path}: {e}")

        if prune_list and not dry_run:
            self._cleanup_empty_dirs(self.artifacts_path)

        return summary

    def expand_glob(self, pattern: str) -> list[str]:
        """Expand glob pattern to list of matching file paths.

        Args:
            pattern: Glob pattern relative to warehouse root (e.g., "knowledge/**/*.md")

        Returns:
            List of relative paths matching the pattern (files only, not directories)
        """
        # Glob from warehouse root
        matches = self.warehouse_path.glob(pattern)

        # Filter to files only and return relative paths
        relative_paths = []
        for match in matches:
            if match.is_file():
                rel_path = match.relative_to(self.warehouse_path)
                relative_paths.append(str(rel_path))

        return relative_paths

    def list_artifacts(self, artifact_type: str | None = None) -> dict[str, list[str]]:
        """List synced artifacts by type.

        Returns a mapping of artifact type (contexts/knowledge/skills) to
        sorted lists of relative paths. If artifact_type is specified,
        only that type is included.
        """
        types_to_show = (
            [artifact_type] if artifact_type else ["contexts", "knowledge", "skills"]
        )
        result: dict[str, list[str]] = {}
        for section in types_to_show:
            section_dir = self.artifacts_path / section
            if not section_dir.exists():
                continue
            files = sorted(
                str(f.relative_to(self.artifacts_path))
                for f in section_dir.rglob("*")
                if f.is_file() and not f.name.startswith(".")
            )
            if files:
                result[section] = files
        return result

    def expand_artifact_paths(self, patterns: list[str]) -> list[str]:
        """Expand artifact path patterns to concrete file paths.

        Handles:
        - Glob patterns (with * or ?)
        - Skill directories (ending with /)
        - Knowledge directories (expanded to **/*.md)
        - Single files

        Returns list of warehouse-relative paths.
        """
        import glob as glob_mod

        expanded: list[str] = []
        for pattern in patterns:
            if "*" in pattern or "?" in pattern:
                matches = [
                    str(Path(p).relative_to(self.warehouse_path))
                    for p in glob_mod.glob(
                        str(self.warehouse_path / pattern), recursive=True
                    )
                    if Path(p).is_file()
                ]
                expanded.extend(matches)
            elif pattern.endswith("/"):
                skill_dir = self.warehouse_path / pattern.rstrip("/")
                if skill_dir.is_dir():
                    for f in skill_dir.rglob("*"):
                        if f.is_file():
                            expanded.append(str(f.relative_to(self.warehouse_path)))
            elif (self.warehouse_path / pattern).is_dir():
                for f in (self.warehouse_path / pattern).rglob("*.md"):
                    if f.is_file():
                        expanded.append(str(f.relative_to(self.warehouse_path)))
            else:
                expanded.append(pattern)
        return expanded

    def files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content using hash comparison.

        Args:
            file1: First file path
            file2: Second file path

        Returns:
            True if files have same content, False otherwise
        """
        try:
            hash1 = self._compute_file_hash(file1)
            hash2 = self._compute_file_hash(file2)
            return hash1 == hash2
        except OSError:
            return False

    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """Private alias for files_identical (backward-compat internal callers)."""
        return self.files_identical(file1, file2)

    def classify_conflicts(self, artifact_paths: list[str]) -> list[str]:
        """Return list of relative paths where local content differs from warehouse.

        A conflict is any path where both the warehouse source and the local
        destination exist but their content differs. Fresh files (dest absent) are
        not conflicts.

        Args:
            artifact_paths: Relative paths to check (e.g. "knowledge/doc.md")

        Returns:
            List of conflicting relative paths
        """
        conflicts = []
        for rel_path in artifact_paths:
            source = self.warehouse_path / rel_path
            dest = self.artifacts_path / rel_path
            if (
                source.exists()
                and dest.exists()
                and not self.files_identical(source, dest)
            ):
                conflicts.append(rel_path)
        return conflicts

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _cleanup_empty_dirs(self, root: Path) -> None:
        """Remove empty directories recursively.

        Args:
            root: Root directory to clean
        """
        for dirpath in sorted(root.rglob("*"), reverse=True):
            if dirpath.is_dir() and not any(dirpath.iterdir()):
                dirpath.rmdir()
