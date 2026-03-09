"""Delta comparison for local artifacts vs warehouse.

This module implements hash-based and diff-based comparison between
local project artifacts and warehouse source files.
"""

import hashlib
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class DeltaStatus(Enum):
    """Status of a compared artifact."""
    IDENTICAL = "identical"
    MODIFIED = "modified"
    ADDED = "added"       # Exists locally but not in warehouse
    MISSING = "missing"   # In beacon.yaml but not synced locally


@dataclass
class ComparisonResult:
    """Result of comparing a single artifact."""
    path: str
    status: DeltaStatus
    local_hash: Optional[str] = None
    warehouse_hash: Optional[str] = None


@dataclass
class DeltaSummary:
    """Summary of all artifact comparisons."""
    results: List[ComparisonResult] = field(default_factory=list)

    @property
    def modified(self) -> List[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.MODIFIED]

    @property
    def added(self) -> List[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.ADDED]

    @property
    def missing(self) -> List[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.MISSING]

    @property
    def identical(self) -> List[ComparisonResult]:
        return [r for r in self.results if r.status == DeltaStatus.IDENTICAL]

    @property
    def has_differences(self) -> bool:
        return any(r.status != DeltaStatus.IDENTICAL for r in self.results)


class DeltaComparator:
    """Compares local artifacts against warehouse versions.

    Supports hash-based summary comparison and detailed git diff.
    Only compares artifacts declared in beacon.yaml.
    """

    def __init__(self, warehouse_path: Path, artifacts_path: Path):
        """Initialize comparator with warehouse and artifacts paths.

        Args:
            warehouse_path: Path to warehouse directory
            artifacts_path: Path to .agentic-beacon/artifacts/ directory

        Raises:
            ValueError: If paths are invalid
        """
        self.warehouse_path = Path(warehouse_path).resolve()
        self.artifacts_path = Path(artifacts_path).resolve()

        if not self.warehouse_path.is_dir():
            raise ValueError(f"Warehouse path is not a valid directory: {warehouse_path}")

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
        with open(actual_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def compare_file(self, relative_path: str) -> ComparisonResult:
        """Compare a single artifact between local and warehouse.

        Args:
            relative_path: Relative path from artifacts/warehouse root

        Returns:
            ComparisonResult with status and hashes
        """
        local_file = self.artifacts_path / relative_path
        warehouse_file = self.warehouse_path / relative_path

        local_exists = local_file.is_file()
        warehouse_exists = warehouse_file.is_file()

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

    def compare_all(self, artifact_paths: Optional[List[str]] = None) -> DeltaSummary:
        """Compare all artifacts.

        Args:
            artifact_paths: List of relative paths to compare.
                If None, compares all files in artifacts directory.

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

        return summary

    def compare_from_config(self, beacon_settings) -> DeltaSummary:
        """Compare only artifacts listed in beacon.yaml.

        Args:
            beacon_settings: Parsed BeaconSettings object

        Returns:
            DeltaSummary for beacon.yaml artifacts only
        """
        from .sync import SyncEngine

        # Collect all artifact paths, expanding globs
        artifact_paths = []
        sync_engine = SyncEngine(
            warehouse_path=self.warehouse_path,
            artifacts_path=self.artifacts_path,
        )

        for artifact_type in ["knowledge", "skills", "contexts"]:
            patterns = getattr(beacon_settings.artifacts, artifact_type)
            for pattern in patterns:
                if "*" in pattern or "?" in pattern or "[" in pattern:
                    matches = sync_engine.expand_glob(pattern)
                    artifact_paths.extend(matches)
                else:
                    artifact_paths.append(pattern)

        return self.compare_all(artifact_paths)

    def detailed_diff(self, relative_path: str, color: bool = True) -> str:
        """Get detailed line-by-line diff using git diff --no-index.

        Args:
            relative_path: Relative path of the artifact to diff
            color: Whether to include ANSI color codes

        Returns:
            Unified diff string, or empty string if identical
        """
        local_file = self.artifacts_path / relative_path
        warehouse_file = self.warehouse_path / relative_path

        if not local_file.exists():
            return f"Local file not found: {relative_path}"

        if not warehouse_file.exists():
            return f"Warehouse file not found: {relative_path}"

        # Use git diff --no-index for comparison
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
        try:
            lines1 = file1.read_text().splitlines()
            lines2 = file2.read_text().splitlines()
        except Exception as e:
            return f"Error reading files: {e}"

        import difflib
        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile=f"warehouse/{file1.name}",
            tofile=f"local/{file2.name}",
            lineterm="",
        )
        return "\n".join(diff)
