"""Sync engine for symlink-based artifact distribution.

This module implements the new symlink-based sync model:
- Per-file symlinks with absolute targets into the warehouse clone
- Real directories at intermediate levels
- Idempotent (skips correct symlinks, repairs broken/wrong-target ones)
- Out-of-warehouse guard (aborts if any beacon.yaml entry resolves outside warehouse)
- Orphan pruning (removes symlinks for dropped entries, leaves regular files for migration)
"""

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from pydantic import BaseModel


class SyncResult(BaseModel):
    """Result of a sync operation on a single file."""

    success: bool
    action: str  # "created", "skipped", "updated", "removed", "error"
    source_path: Path | None = None
    dest_path: Path | None = None
    error_message: str | None = None

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class SyncSummary:
    """Summary of a full sync operation."""

    created: int = 0
    skipped: int = 0
    updated: int = 0
    removed: int = 0
    errors: int = 0
    failed_files: list[tuple[str, str]] = field(default_factory=list)
    results: list[SyncResult] = field(default_factory=list)
    log_messages: list[str] = field(default_factory=list)
    pruned_paths: list[str] = field(default_factory=list)


class OutOfWarehouseError(Exception):
    """Raised when a beacon.yaml entry resolves outside the warehouse root."""

    def __init__(self, entry: str, resolved_path: Path) -> None:
        self.entry = entry
        self.resolved_path = resolved_path
        super().__init__(
            f"Entry '{entry}' resolves outside the warehouse: {resolved_path}"
        )


@dataclass
class SyncEngine:
    """Engine for syncing artifacts from warehouse to project via symlinks."""

    warehouse_path: Path
    artifacts_path: Path

    def __post_init__(self) -> None:
        """Normalize paths."""
        self.warehouse_path = Path(self.warehouse_path).resolve()
        self.artifacts_path = Path(self.artifacts_path).resolve()
        logger.debug(
            "SyncEngine initialized: warehouse={}, artifacts={}",
            self.warehouse_path,
            self.artifacts_path,
        )

    def verify_in_warehouse(self, relative_path: str) -> Path:
        """Resolve a relative path and verify it lives inside the warehouse.

        Raises OutOfWarehouseError if the resolved path is outside.
        """
        source = self.warehouse_path / relative_path
        resolved = source.resolve()
        # Ensure the resolved path is a descendant of the warehouse root
        try:
            resolved.relative_to(self.warehouse_path)
        except ValueError:
            raise OutOfWarehouseError(relative_path, resolved) from None
        return resolved

    def create_symlink(self, relative_path: str) -> SyncResult:
        """Create or repair a symlink for a single artifact.

        Returns SyncResult indicating what happened.
        """
        try:
            source = self.verify_in_warehouse(relative_path)
        except OutOfWarehouseError as e:
            return SyncResult(
                success=False,
                action="error",
                error_message=str(e),
            )

        if not source.exists():
            return SyncResult(
                success=False,
                action="error",
                error_message=f"Source file not found: {source}",
            )

        dest = self.artifacts_path / relative_path
        target = str(source)

        # Ensure parent directories exist (real directories, not symlinks)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists() or dest.is_symlink():
            if dest.is_symlink():
                current_target = os.readlink(dest)
                if current_target == target:
                    # Correct symlink already exists
                    return SyncResult(
                        success=True,
                        action="skipped",
                        source_path=source,
                        dest_path=dest,
                    )
                # Wrong target or broken — remove and recreate
                dest.unlink()
            else:
                # Regular file exists — this is a migration case, handled separately
                return SyncResult(
                    success=True,
                    action="skipped",
                    source_path=source,
                    dest_path=dest,
                )

        # Create the symlink
        try:
            dest.symlink_to(target)
            return SyncResult(
                success=True,
                action="created",
                source_path=source,
                dest_path=dest,
            )
        except OSError as e:
            return SyncResult(
                success=False,
                action="error",
                source_path=source,
                dest_path=dest,
                error_message=str(e),
            )

    def remove_symlink(self, relative_path: str) -> SyncResult:
        """Remove a symlink (only if it's a symlink, not a regular file)."""
        dest = self.artifacts_path / relative_path
        if dest.is_symlink():
            try:
                dest.unlink()
                return SyncResult(
                    success=True,
                    action="removed",
                    dest_path=dest,
                )
            except OSError as e:
                return SyncResult(
                    success=False,
                    action="error",
                    dest_path=dest,
                    error_message=str(e),
                )
        return SyncResult(
            success=True,
            action="skipped",
            dest_path=dest,
        )

    def sync_all(
        self,
        artifact_paths: list[str],
        paths_to_prune: list[str] | None = None,
        verbose: bool = False,
        dry_run: bool = False,
        log_fn: Callable[[str], None] | None = None,
    ) -> SyncSummary:
        """Sync all artifacts via symlinks.

        Args:
            artifact_paths: List of relative paths to sync
            paths_to_prune: Explicit list of relative paths to remove
            verbose: If True, log detailed operations
            dry_run: If True, preview actions without making changes
            log_fn: Optional callback for log messages

        Returns:
            SyncSummary with operation counts
        """
        summary = SyncSummary()

        def log(msg: str) -> None:
            summary.log_messages.append(msg)
            if log_fn:
                log_fn(msg)

        # First, validate all paths are inside the warehouse
        for path in artifact_paths:
            try:
                self.verify_in_warehouse(path)
            except OutOfWarehouseError:
                # Re-raise to abort the entire sync
                raise

        # Create symlinks
        for path in artifact_paths:
            if verbose or dry_run:
                log(f"Syncing: {path}")

            if dry_run:
                result = self._preview_symlink(path)
            else:
                result = self.create_symlink(path)

            summary.results.append(result)

            if result.action == "created":
                summary.created += 1
                if verbose or dry_run:
                    log(f"  {'Would create' if dry_run else 'Created'}: {path}")
            elif result.action == "skipped":
                summary.skipped += 1
                if verbose or dry_run:
                    log(f"  {'Would skip' if dry_run else 'Skipped'}: {path}")
            elif result.action == "updated":
                summary.updated += 1
                if verbose or dry_run:
                    log(f"  {'Would update' if dry_run else 'Updated'}: {path}")
            elif result.action == "error":
                summary.errors += 1
                summary.failed_files.append(
                    (path, result.error_message or "unknown error")
                )
                log(f"  Error: {path} - {result.error_message}")

        # Prune orphans
        prune_list = paths_to_prune or []
        for rel_path in prune_list:
            if dry_run:
                summary.removed += 1
                if verbose or dry_run:
                    log(f"  Would remove: {rel_path}")
            else:
                result = self.remove_symlink(rel_path)
                if result.action == "removed":
                    summary.removed += 1
                    summary.pruned_paths.append(rel_path)
                    if verbose:
                        log(f"  Removed: {rel_path}")
                elif result.action == "error":
                    summary.errors += 1
                    summary.failed_files.append(
                        (rel_path, result.error_message or "unknown error")
                    )

        if prune_list and not dry_run:
            self._cleanup_empty_dirs(self.artifacts_path)

        return summary

    def _preview_symlink(self, relative_path: str) -> SyncResult:
        """Preview what would happen for a symlink without creating it."""
        try:
            source = self.verify_in_warehouse(relative_path)
        except OutOfWarehouseError as e:
            return SyncResult(
                success=False,
                action="error",
                error_message=str(e),
            )

        if not source.exists():
            return SyncResult(
                success=False,
                action="error",
                error_message=f"Source file not found: {source}",
            )

        dest = self.artifacts_path / relative_path
        target = str(source)

        if dest.exists() or dest.is_symlink():
            if dest.is_symlink():
                current_target = os.readlink(dest)
                if current_target == target:
                    return SyncResult(
                        success=True,
                        action="skipped",
                        source_path=source,
                        dest_path=dest,
                    )
                return SyncResult(
                    success=True,
                    action="updated",
                    source_path=source,
                    dest_path=dest,
                )
            return SyncResult(
                success=True,
                action="skipped",
                source_path=source,
                dest_path=dest,
            )

        return SyncResult(
            success=True,
            action="created",
            source_path=source,
            dest_path=dest,
        )

    def expand_glob(self, pattern: str) -> list[str]:
        """Expand glob pattern to list of matching file paths."""
        matches = self.warehouse_path.glob(pattern)
        relative_paths = []
        for match in matches:
            if match.is_file():
                rel_path = match.relative_to(self.warehouse_path)
                relative_paths.append(str(rel_path))
        return relative_paths

    def list_artifacts(self, artifact_type: str | None = None) -> dict[str, list[str]]:
        """List synced artifacts by type."""
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
                if f.is_symlink() and not f.name.startswith(".")
            )
            if files:
                result[section] = files
        return result

    def files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content using hash comparison."""
        try:
            hash1 = self._compute_file_hash(file1)
            hash2 = self._compute_file_hash(file2)
            return hash1 == hash2
        except OSError:
            return False

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _cleanup_empty_dirs(self, root: Path) -> None:
        """Remove empty directories recursively."""
        for dirpath in sorted(root.rglob("*"), reverse=True):
            if dirpath.is_dir() and not any(dirpath.iterdir()):
                dirpath.rmdir()

    def classify_entries(
        self,
        artifact_paths: list[str],
    ) -> dict[str, str]:
        """Classify each beacon.yaml-matched entry in the artifacts directory.

        Returns dict keyed by relative path with values:
        - "symlink_ok" — symlink pointing to correct warehouse file
        - "symlink_broken" — symlink pointing to missing target
        - "regular_file_identical" — regular file, byte-equal to warehouse
        - "regular_file_modified" — regular file, differs from warehouse
        - "missing" — not present in artifacts directory
        """
        result: dict[str, str] = {}
        for rel_path in artifact_paths:
            dest = self.artifacts_path / rel_path
            source = self.warehouse_path / rel_path

            if dest.is_symlink():
                if not dest.exists():
                    result[rel_path] = "symlink_broken"
                else:
                    resolved = dest.resolve()
                    expected = source.resolve()
                    result[rel_path] = (
                        "symlink_ok" if resolved == expected else "symlink_broken"
                    )
            elif dest.exists() and dest.is_file():
                if source.exists():
                    if self.files_identical(source, dest):
                        result[rel_path] = "regular_file_identical"
                    else:
                        result[rel_path] = "regular_file_modified"
                else:
                    result[rel_path] = "regular_file_modified"
            else:
                result[rel_path] = "missing"

        return result
