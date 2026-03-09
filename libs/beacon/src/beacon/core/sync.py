"""Sync engine for snapshot-based artifact copying.

This module implements pure copy (no symlinks) syncing of artifacts
from warehouse to project's .agentic-beacon/artifacts/ directory.
"""

import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    action: str  # "copied", "skipped", "preserved", "error"
    source_path: Optional[Path] = None
    dest_path: Optional[Path] = None
    error_message: Optional[str] = None


@dataclass
class SyncSummary:
    """Summary of a full sync operation."""

    copied: int = 0
    skipped: int = 0
    preserved: int = 0
    pruned: int = 0
    errors: int = 0
    results: List[SyncResult] = field(default_factory=list)
    log_messages: List[str] = field(default_factory=list)


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

    def __init__(self, warehouse_path: Path, artifacts_path: Path):
        """Initialize sync engine.

        Args:
            warehouse_path: Path to warehouse directory
            artifacts_path: Path to .agentic-beacon/artifacts/ directory
        """
        self.warehouse_path = Path(warehouse_path)
        self.artifacts_path = Path(artifacts_path)

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

        try:
            # Check if source exists
            if not source_file.exists():
                return SyncResult(
                    success=False,
                    action="error",
                    source_path=source_file,
                    error_message=f"Source file not found: {source_file}"
                )

            # Check if destination exists and is unchanged (idempotent check)
            if dest_file.exists():
                if self._files_identical(source_file, dest_file):
                    return SyncResult(
                        success=True,
                        action="skipped",
                        source_path=source_file,
                        dest_path=dest_file
                    )

                # File differs - check preserve flag
                if preserve:
                    return SyncResult(
                        success=True,
                        action="preserved",
                        source_path=source_file,
                        dest_path=dest_file
                    )

            # Create parent directories
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (always as regular file, never as symlink)
            if source_file.is_symlink():
                # If source is symlink, copy the target content
                shutil.copy2(source_file.resolve(), dest_file)
            else:
                shutil.copy2(source_file, dest_file)

            return SyncResult(
                success=True,
                action="copied",
                source_path=source_file,
                dest_path=dest_file
            )

        except Exception as e:
            return SyncResult(
                success=False,
                action="error",
                source_path=source_file,
                error_message=str(e)
            )

    def sync_all(
        self,
        artifact_paths: List[str],
        preserve: bool = False,
        prune: bool = False,
        verbose: bool = False,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> SyncSummary:
        """Sync all artifacts from a list of paths.

        Args:
            artifact_paths: List of relative paths to sync
            preserve: If True, skip locally modified files
            prune: If True, remove artifacts not in the list
            verbose: If True, log detailed operations
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
            if verbose:
                log(f"Syncing: {path}")

            result = self.copy_file(path, preserve=preserve)
            summary.results.append(result)

            if result.action == "copied":
                summary.copied += 1
                if verbose:
                    log(f"  Copied: {path}")
            elif result.action == "skipped":
                summary.skipped += 1
                if verbose:
                    log(f"  Unchanged: {path}")
            elif result.action == "preserved":
                summary.preserved += 1
                if verbose:
                    log(f"  Preserved (local changes): {path}")
            elif result.action == "error":
                summary.errors += 1
                log(f"  Error: {path} - {result.error_message}")

        # Prune artifacts not in the list
        if prune and self.artifacts_path.exists():
            synced_set = set(artifact_paths)
            for file_path in sorted(self.artifacts_path.rglob("*")):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(self.artifacts_path))
                    if rel_path not in synced_set:
                        try:
                            file_path.unlink()
                            summary.pruned += 1
                            if verbose:
                                log(f"  Pruned: {rel_path}")
                        except Exception as e:
                            summary.errors += 1
                            log(f"  Error pruning {rel_path}: {e}")

            # Clean up empty directories after pruning
            self._cleanup_empty_dirs(self.artifacts_path)

        return summary

    def expand_glob(self, pattern: str) -> List[str]:
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

    def _files_identical(self, file1: Path, file2: Path) -> bool:
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
        except Exception:
            return False

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
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
