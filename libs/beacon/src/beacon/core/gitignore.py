"""Gitignore management for Agentic Beacon.

Automatically manages .gitignore entries to ensure:
- .agentic-beacon/config.toml is excluded (local config)
- .agentic-beacon/artifacts/ is excluded (synced copies)
- .agentic-beacon/beacon.yaml is NOT excluded (team config)
"""

from pathlib import Path

from loguru import logger


# Entries that should be in .gitignore
GITIGNORE_ENTRIES = [
    ".agentic-beacon/config.toml",
    ".agentic-beacon/artifacts/",
    ".agentic-beacon/warehouse-catalog.md",
]

# Section header for our entries
SECTION_HEADER = "# Agentic Beacon"


class GitignoreManager:
    """Manages .gitignore entries for agentic-beacon files."""

    def __init__(self, project_root: Path | str = "."):
        """Initialize with project root directory.

        Args:
            project_root: Path to project root containing .gitignore
        """
        self.project_root = Path(project_root).resolve()
        self.gitignore_path = self.project_root / ".gitignore"

    def ensure_entries(self, entries: list[str] | None = None) -> bool:
        """Ensure all required entries are in .gitignore.

        Creates .gitignore if it doesn't exist.
        Appends entries only if they're missing.

        Args:
            entries: Specific entries to add. Defaults to GITIGNORE_ENTRIES.

        Returns:
            True if .gitignore was modified, False if no changes needed

        Raises:
            PermissionError: If cannot write to .gitignore
        """
        entries = entries or GITIGNORE_ENTRIES

        if self.gitignore_path.exists():
            existing_content = self.gitignore_path.read_text(encoding="utf-8")
            existing_lines = set(existing_content.splitlines())
        else:
            existing_content = ""
            existing_lines = set()

        # Find missing entries
        missing_entries = [e for e in entries if e not in existing_lines]

        if not missing_entries:
            logger.debug("No .gitignore entries to add")
            return False  # No changes needed

        # Build new content to append
        new_lines = []

        # Add section header if not present
        if SECTION_HEADER not in existing_lines:
            new_lines.append(SECTION_HEADER)

        for entry in missing_entries:
            new_lines.append(entry)

        # Append to existing content
        if existing_content and not existing_content.endswith("\n"):
            prefix = "\n\n"
        elif existing_content:
            prefix = "\n"
        else:
            prefix = ""

        new_content = existing_content + prefix + "\n".join(new_lines) + "\n"

        try:
            self.gitignore_path.write_text(new_content, encoding="utf-8")
            logger.debug("Updated .gitignore with {} entries: {}", len(missing_entries), missing_entries)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot write to {self.gitignore_path}: {e}"
            ) from e

        return True

    def has_entry(self, entry: str) -> bool:
        """Check if a specific entry exists in .gitignore.

        Args:
            entry: The gitignore entry to check for

        Returns:
            True if entry exists in .gitignore
        """
        if not self.gitignore_path.exists():
            return False

        existing_content = self.gitignore_path.read_text(encoding="utf-8")
        existing_lines = set(existing_content.splitlines())
        return entry in existing_lines

    def verify_beacon_yaml_not_ignored(self) -> bool:
        """Verify that beacon.yaml is NOT being ignored.

        Returns:
            True if beacon.yaml is safe (not ignored), False if it's being ignored
        """
        if not self.gitignore_path.exists():
            return True  # No .gitignore means nothing is ignored

        content = self.gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        beacon_patterns = [
            "beacon.yaml",
            ".agentic-beacon/beacon.yaml",
            ".agentic-beacon/*",
            ".agentic-beacon/",
        ]

        for line in lines:
            stripped = line.strip()
            if stripped in beacon_patterns and not stripped.startswith("!"):
                return False  # beacon.yaml might be ignored

        return True
