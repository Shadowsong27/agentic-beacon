"""Warehouse initialization logic."""

import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from beacon.domains.artifact.checksums import compute_sha256, write_checksums

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
TEMPLATES_DIR = _DATA_DIR / "templates"

# Relative paths (from warehouse root) of all template-generated files.
# Keep in sync with _create_* methods below.
TEMPLATE_FILES: list[str] = [
    ".gitignore",
    "README.md",
    "agents/README.md",
    "contexts/README.md",
    "docs/architecture.md",
    "docs/contribution-guide.md",
    "knowledge/README.md",
    "skills/README.md",
    "skills/record-knowledge/SKILL.md",
]


class WarehouseInitializer:
    """Handles creation of new warehouse repositories."""

    def __init__(self, *, warehouse_path: Path):
        """
        Initialize warehouse initializer.

        Args:
            warehouse_path: Path where warehouse will be created
        """
        self.warehouse_path = warehouse_path

    def init(
        self,
        *,
        org_name: str = "Your Organization",
        languages: list[str] | None = None,
        domains: list[str] | None = None,
        init_git: bool = True,
    ) -> dict[str, Any]:
        """
        Initialize a new warehouse repository.

        When the target directory already exists (e.g. a freshly cloned empty
        repo), initialization proceeds in-place: existing files are left
        untouched and only missing files are created.

        Args:
            org_name: Organization name for documentation
            languages: Ignored — inner knowledge structure is user-defined
            domains: Ignored — inner knowledge structure is user-defined
            init_git: Whether to initialize git repository

        Returns:
            Result dictionary with created paths and ``in_place`` flag
        """
        in_place = self.warehouse_path.exists()

        logger.info(
            f"Initializing warehouse at {self.warehouse_path} "
            f"({'in-place' if in_place else 'new directory'})"
        )

        # Create directory structure
        self._create_structure()

        # Create starter files
        self._create_contexts()
        self._create_knowledge()
        self._create_skills()
        self._create_docs(org_name)
        self._create_root_files(org_name)
        self._install_bundled_skills()

        # Write checksum file atomically after all template writes succeed
        self._write_template_checksums()

        # Initialize git if requested
        if init_git:
            self._init_git()

        result = {
            "warehouse_path": str(self.warehouse_path),
            "git_initialized": init_git,
            "in_place": in_place,
        }

        logger.info(f"Warehouse initialized successfully: {result}")
        return result

    def _create_structure(self) -> None:
        """Create required directory structure (skips dirs that already exist)."""
        self.warehouse_path.mkdir(parents=True, exist_ok=True)
        (self.warehouse_path / "agents").mkdir(exist_ok=True)
        (self.warehouse_path / "contexts").mkdir(exist_ok=True)
        (self.warehouse_path / "knowledge").mkdir(exist_ok=True)
        (self.warehouse_path / "skills").mkdir(exist_ok=True)
        (self.warehouse_path / "docs").mkdir(exist_ok=True)
        self._create_agents()

    def _write_if_missing(self, path: Path, content: str) -> None:
        """Write *content* to *path* only when the file does not already exist."""
        if not path.exists():
            path.write_text(content)
        else:
            logger.debug(f"Skipping existing file: {path}")

    def _render_template(self, rel_path: str, org_name: str) -> str:
        """Read a template file and substitute the org_name placeholder."""
        content = (TEMPLATES_DIR / rel_path).read_text(encoding="utf-8")
        return content.replace("{org_name}", org_name)

    def _create_agents(self) -> None:
        """Create agents directory with README template."""
        self._write_if_missing(
            self.warehouse_path / "agents" / "README.md",
            (TEMPLATES_DIR / "agents" / "README.md").read_text(encoding="utf-8"),
        )

    def _create_contexts(self) -> None:
        """Create starter context file."""
        self._write_if_missing(
            self.warehouse_path / "contexts" / "README.md",
            self._render_template("contexts/README.md", ""),
        )

    def _create_knowledge(self) -> None:
        """Create starter knowledge file."""
        self._write_if_missing(
            self.warehouse_path / "knowledge" / "README.md",
            self._render_template("knowledge/README.md", ""),
        )

    def _create_skills(self) -> None:
        """Create skills structure."""
        self._write_if_missing(
            self.warehouse_path / "skills" / "README.md",
            self._render_template("skills/README.md", ""),
        )

    def _create_docs(self, org_name: str) -> None:
        """Create documentation files."""
        self._write_if_missing(
            self.warehouse_path / "docs" / "architecture.md",
            self._render_template("docs/architecture.md", org_name),
        )
        self._write_if_missing(
            self.warehouse_path / "docs" / "contribution-guide.md",
            self._render_template("docs/contribution-guide.md", org_name),
        )

    def _create_root_files(self, org_name: str) -> None:
        """Create root-level files."""
        self._write_if_missing(
            self.warehouse_path / "README.md",
            self._render_template("README.md", org_name),
        )
        self._write_if_missing(
            self.warehouse_path / ".gitignore",
            (TEMPLATES_DIR / ".gitignore").read_text(encoding="utf-8"),
        )

    def _install_bundled_skills(self) -> None:
        """Add abc-provided skills to the warehouse skills directory (skips existing)."""
        bundled_skills_dir = _DATA_DIR / "skills"
        for skill_dir in bundled_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            content = skill_md.read_text(encoding="utf-8")
            dest_dir = self.warehouse_path / "skills" / skill_dir.name
            dest_dir.mkdir(parents=True, exist_ok=True)
            self._write_if_missing(dest_dir / "SKILL.md", content)

        logger.info("Bundled skills installed")

    def _write_template_checksums(self) -> None:
        """Compute SHA256 for each template-generated file and write the checksum file."""
        file_hashes: dict[str, str] = {}
        for rel in TEMPLATE_FILES:
            path = self.warehouse_path / rel
            if path.exists():
                content = path.read_text(encoding="utf-8")
                file_hashes[rel] = compute_sha256(content)
        write_checksums(self.warehouse_path, file_hashes)
        logger.debug(f"Template checksums written for {len(file_hashes)} files")

    def _init_git(self) -> None:
        """Initialize git repository with initial commit.

        Skips ``git init`` when the directory already has a ``.git`` folder
        (e.g. a freshly cloned empty repo), but still stages and commits any
        newly created files.
        """
        try:
            if not (self.warehouse_path / ".git").exists():
                subprocess.run(
                    ["git", "init"],
                    cwd=self.warehouse_path,
                    check=True,
                    capture_output=True,
                )
            subprocess.run(
                ["git", "add", "."],
                cwd=self.warehouse_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "feat: initialize warehouse with beacon"],
                cwd=self.warehouse_path,
                check=True,
                capture_output=True,
            )
            logger.info("Git repository initialized with initial commit")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git initialization failed: {e}")
            raise
        except FileNotFoundError:
            logger.warning("Git not found in PATH, skipping git initialization")
