"""Sync engine for snapshot-based artifact copying.

This module implements pure copy (no symlinks) syncing of artifacts
from warehouse to project's .agentic-beacon/artifacts/ directory.
"""

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class SyncResult:
    """Result of a sync operation."""
    
    success: bool
    action: str  # "copied", "skipped", "error"
    source_path: Optional[Path] = None
    dest_path: Optional[Path] = None
    error_message: Optional[str] = None


class SyncEngine:
    """Engine for syncing artifacts from warehouse to project.
    
    Implements snapshot-based pure copy model:
    - No symlinks (for agent compatibility)
    - Idempotent (skips unchanged files)
    - Preserves directory structure
    - Supports glob patterns
    """
    
    def __init__(self, warehouse_path: Path, artifacts_path: Path):
        """Initialize sync engine.
        
        Args:
            warehouse_path: Path to warehouse directory
            artifacts_path: Path to .agentic-beacon/artifacts/ directory
        """
        self.warehouse_path = Path(warehouse_path)
        self.artifacts_path = Path(artifacts_path)
    
    def copy_file(self, relative_path: str) -> SyncResult:
        """Copy a single file from warehouse to artifacts directory.
        
        Args:
            relative_path: Relative path from warehouse root (e.g., "knowledge/doc.md")
        
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
