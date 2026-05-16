"""Core distribution logic for agentic warehouse content."""

import shutil
from pathlib import Path
from typing import Any

from loguru import logger

from beacon.core.file_filter import ARTIFACT_IGNORE_PATTERNS


def is_partial_path(rel: Path | str) -> bool:
    """Return True if the path is under an ``agents/_partials/`` directory.

    Matches the warehouse convention for shared agent partials
    (e.g. ``agents/_partials/deep-review-checklist.md``). The filter is
    intentionally scoped to ``_partials/`` specifically — the same string
    drives co-distribution in ``run_sync`` (``agents/_partials/**/*``), so
    broadening the filter without broadening co-distribution would hide
    files from agent listings while silently failing to ship them.
    """
    parts = Path(rel).parts

    # Accept both warehouse-relative ('agents/_partials/...') and
    # agents-dir-relative ('_partials/...') input. Find the first occurrence
    # of either marker and check the next segment.
    try:
        agents_idx = parts.index("agents")
        return len(parts) > agents_idx + 1 and parts[agents_idx + 1] == "_partials"
    except ValueError:
        return len(parts) > 0 and parts[0] == "_partials"


class WarehouseDistributor:
    """Handles distribution of warehouse content to project .opencode folder."""

    def __init__(self, *, warehouse_root: Path, target_root: Path):
        """
        Initialize distributor.

        Args:
            warehouse_root: Path to warehouse repository root
            target_root: Path to target project root (will create .opencode inside)
        """
        self.warehouse_root = warehouse_root
        self.target_root = target_root
        self.opencode_dir = target_root / ".opencode"

    def setup(
        self,
        *,
        contexts: list[str],
        knowledge_scopes: list[str],
        skills: list[str],
    ) -> dict[str, Any]:
        """
        Distribute selected content to .opencode folder.

        Args:
            contexts: List of context names (e.g., ["global", "python"])
            knowledge_scopes: List of knowledge scopes (e.g., ["global", "languages/python"])
            skills: List of skill names (e.g., ["example-skill"])

        Returns:
            Result dictionary with counts and paths
        """
        logger.info(f"Setting up warehouse content in {self.opencode_dir}")

        # Create .opencode directory structure
        self._create_directory_structure()

        # Distribute content
        result = {
            "contexts": self._distribute_contexts(contexts),
            "knowledge": self._distribute_knowledge(knowledge_scopes),
            "skills": self._distribute_skills(skills),
            "target_dir": str(self.opencode_dir),
        }

        logger.info(f"Setup complete: {result}")
        return result

    def update(self) -> dict[str, Any]:
        """
        Update existing .opencode content from warehouse.

        Returns:
            Result dictionary with updated counts
        """
        if not self.opencode_dir.exists():
            raise ValueError(
                f"No .opencode directory found at {self.opencode_dir}. Run setup first."
            )

        logger.info("Updating warehouse content")

        # Read existing configuration to know what to update
        config = self._read_config()

        # Re-distribute based on existing config
        result = self.setup(
            contexts=config.get("contexts", []),
            knowledge_scopes=config.get("knowledge_scopes", []),
            skills=config.get("skills", []),
        )

        logger.info("Update complete")
        return result

    def clean(self) -> bool:
        """
        Remove .opencode directory.

        Returns:
            True if directory was removed, False if it didn't exist
        """
        if self.opencode_dir.exists():
            logger.info(f"Removing {self.opencode_dir}")
            shutil.rmtree(self.opencode_dir)
            return True

        logger.info(f"No .opencode directory found at {self.opencode_dir}")
        return False

    def list_available(self) -> dict[str, list[str]]:
        """
        List all available content in warehouse.

        Returns:
            Dictionary with agents, contexts, knowledge, and skills lists
        """
        agents_dir = self.warehouse_root / "agents"
        contexts_dir = self.warehouse_root / "contexts"
        knowledge_dir = self.warehouse_root / "knowledge"
        skills_dir = self.warehouse_root / "skills"

        return {
            "agents": self._list_agents(agents_dir),
            "contexts": self._list_contexts(contexts_dir),
            "knowledge": self._list_knowledge(knowledge_dir),
            "skills": self._list_skills(skills_dir),
        }

    def delta(self) -> dict[str, Any]:
        """
        Compare target .opencode with warehouse to find differences.

        Detects:
        - New files in target (potential contributions back to warehouse)
        - Modified files in target (local customizations)
        - Files in warehouse but not in target (missing content)

        Returns:
            Dictionary with new_in_target, modified_in_target, missing_in_target lists
        """

        if not self.opencode_dir.exists():
            raise ValueError(
                f"No .opencode directory found at {self.opencode_dir}. Run setup first."
            )

        logger.info("Comparing target with warehouse")

        config = self._read_config()
        contexts = config.get("contexts", [])
        knowledge_scopes = config.get("knowledge_scopes", [])
        skills = config.get("skills", [])

        new_in_target = []
        modified_in_target = []
        missing_in_target = []

        # Check contexts
        for context in contexts:
            warehouse_file = self.warehouse_root / "contexts" / f"AGENTS.{context}.md"
            target_file = self.opencode_dir / "contexts" / f"AGENTS.{context}.md"

            if target_file.exists():
                if warehouse_file.exists():
                    # Compare hashes
                    if not self._files_identical(warehouse_file, target_file):
                        modified_in_target.append(f"contexts/AGENTS.{context}.md")
                else:
                    new_in_target.append(f"contexts/AGENTS.{context}.md")
            elif warehouse_file.exists():
                missing_in_target.append(f"contexts/AGENTS.{context}.md")

        # Check knowledge files
        for scope in knowledge_scopes:
            warehouse_dir = self.warehouse_root / "knowledge" / scope
            target_dir = self.opencode_dir / "knowledge" / scope

            if not warehouse_dir.exists() or not target_dir.exists():
                continue

            # Get all markdown files in both directories
            warehouse_files = {
                f.relative_to(warehouse_dir): f for f in warehouse_dir.rglob("*.md")
            }
            target_files = {
                f.relative_to(target_dir): f for f in target_dir.rglob("*.md")
            }

            # Find new files in target
            for rel_path in target_files:
                if rel_path not in warehouse_files:
                    new_in_target.append(f"knowledge/{scope}/{rel_path}")
                elif not self._files_identical(
                    warehouse_files[rel_path], target_files[rel_path]
                ):
                    modified_in_target.append(f"knowledge/{scope}/{rel_path}")

            # Find missing files in target
            for rel_path in warehouse_files:
                if rel_path not in target_files:
                    missing_in_target.append(f"knowledge/{scope}/{rel_path}")

        # Check skills
        for skill in skills:
            warehouse_dir = self.warehouse_root / "skills" / skill
            target_dir = self.opencode_dir / "skills" / skill

            if not warehouse_dir.exists() or not target_dir.exists():
                continue

            warehouse_files = {
                f.relative_to(warehouse_dir): f
                for f in warehouse_dir.rglob("*")
                if f.is_file()
            }
            target_files = {
                f.relative_to(target_dir): f
                for f in target_dir.rglob("*")
                if f.is_file()
            }

            for rel_path in target_files:
                if rel_path not in warehouse_files:
                    new_in_target.append(f"skills/{skill}/{rel_path}")
                elif not self._files_identical(
                    warehouse_files[rel_path], target_files[rel_path]
                ):
                    modified_in_target.append(f"skills/{skill}/{rel_path}")

            for rel_path in warehouse_files:
                if rel_path not in target_files:
                    missing_in_target.append(f"skills/{skill}/{rel_path}")

        result = {
            "new_in_target": new_in_target,
            "modified_in_target": modified_in_target,
            "missing_in_target": missing_in_target,
        }

        logger.info(
            f"Delta complete: {len(new_in_target)} new, {len(modified_in_target)} modified, {len(missing_in_target)} missing"
        )
        return result

    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files have identical content using SHA256."""
        import hashlib

        def file_hash(path: Path) -> str:
            sha256 = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()

        return file_hash(file1) == file_hash(file2)

    def _create_directory_structure(self) -> None:
        """Create .opencode directory structure."""
        self.opencode_dir.mkdir(exist_ok=True)
        (self.opencode_dir / "contexts").mkdir(exist_ok=True)
        (self.opencode_dir / "knowledge").mkdir(exist_ok=True)
        (self.opencode_dir / "skills").mkdir(exist_ok=True)

    def _distribute_contexts(self, contexts: list[str]) -> int:
        """Distribute context files."""
        count = 0
        contexts_src = self.warehouse_root / "contexts"
        contexts_dst = self.opencode_dir / "contexts"

        for context_name in contexts:
            src_file = contexts_src / f"AGENTS.{context_name}.md"
            if src_file.exists():
                dst_file = contexts_dst / f"AGENTS.{context_name}.md"
                shutil.copy2(src_file, dst_file)
                logger.debug(f"Copied context: {context_name}")
                count += 1
            else:
                logger.warning(f"Context not found: {context_name}")

        return count

    def _distribute_knowledge(self, knowledge_scopes: list[str]) -> int:
        """Distribute knowledge directories."""
        count = 0
        knowledge_src = self.warehouse_root / "knowledge"
        knowledge_dst = self.opencode_dir / "knowledge"

        for scope in knowledge_scopes:
            src_dir = knowledge_src / scope
            if src_dir.exists() and src_dir.is_dir():
                dst_dir = knowledge_dst / scope

                # Copy entire directory tree
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(
                    src_dir,
                    dst_dir,
                    ignore=shutil.ignore_patterns(*ARTIFACT_IGNORE_PATTERNS),
                )

                # Count files
                files = list(dst_dir.rglob("*.md"))
                count += len(files)
                logger.debug(f"Copied knowledge scope: {scope} ({len(files)} files)")
            else:
                logger.warning(f"Knowledge scope not found: {scope}")

        return count

    def _distribute_skills(self, skills: list[str]) -> int:
        """Distribute skill directories."""
        count = 0
        skills_src = self.warehouse_root / "skills"
        skills_dst = self.opencode_dir / "skills"

        for skill_name in skills:
            src_dir = skills_src / skill_name
            if src_dir.exists() and src_dir.is_dir():
                dst_dir = skills_dst / skill_name

                # Copy entire skill directory
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(
                    src_dir,
                    dst_dir,
                    ignore=shutil.ignore_patterns(*ARTIFACT_IGNORE_PATTERNS),
                )

                logger.debug(f"Copied skill: {skill_name}")
                count += 1
            else:
                logger.warning(f"Skill not found: {skill_name}")

        return count

    def _list_agents(self, agents_dir: Path) -> list[str]:
        """List available agent definition files as paths relative to warehouse root."""
        if not agents_dir.exists():
            return []

        agents = []
        for file in sorted(agents_dir.rglob("*.md")):
            if not file.name.startswith(".") and file.name.upper() != "README.MD":
                rel = file.relative_to(agents_dir.parent)
                if is_partial_path(rel):
                    continue
                agents.append(str(rel))

        return sorted(agents)

    def _list_contexts(self, contexts_dir: Path) -> list[str]:
        """List available context files as paths relative to warehouse root."""
        if not contexts_dir.exists():
            return []

        contexts = []
        for file in sorted(contexts_dir.rglob("*.md")):
            if not file.name.startswith(".") and file.name.upper() != "README.MD":
                rel = file.relative_to(contexts_dir.parent)
                contexts.append(str(rel))

        return sorted(contexts)

    def _list_knowledge(self, knowledge_dir: Path) -> list[str]:
        """List available knowledge scopes."""
        if not knowledge_dir.exists():
            return []

        scopes = []

        # List all directories under knowledge/
        for scope_dir in knowledge_dir.iterdir():
            if scope_dir.is_dir() and not scope_dir.name.startswith("."):
                scopes.append(scope_dir.name)

                # List subdirectories (e.g., languages/python)
                for sub_dir in scope_dir.iterdir():
                    if sub_dir.is_dir() and not sub_dir.name.startswith("."):
                        relative_path = f"{scope_dir.name}/{sub_dir.name}"
                        scopes.append(relative_path)

        return sorted(scopes)

    def _list_skills(self, skills_dir: Path) -> list[str]:
        """List available skills."""
        if not skills_dir.exists():
            return []

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir.name)

        return sorted(skills)

    def _read_config(self) -> dict[str, Any]:
        """Read existing .opencode configuration."""
        import yaml

        config_file = self.opencode_dir / ".warehouse-config.yml"

        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f) or {}

        # Fallback: detect from existing structure
        return {
            "contexts": self._detect_installed_contexts(),
            "knowledge_scopes": self._detect_installed_knowledge(),
            "skills": self._detect_installed_skills(),
        }

    def _save_config(
        self,
        *,
        contexts: list[str],
        knowledge_scopes: list[str],
        skills: list[str],
    ) -> None:
        """Save configuration for future updates."""
        import yaml

        config = {
            "contexts": contexts,
            "knowledge_scopes": knowledge_scopes,
            "skills": skills,
        }

        config_file = self.opencode_dir / ".warehouse-config.yml"
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    def _detect_installed_contexts(self) -> list[str]:
        """Detect currently installed contexts."""
        contexts_dir = self.opencode_dir / "contexts"
        if not contexts_dir.exists():
            return []

        contexts = []
        for file in contexts_dir.glob("AGENTS.*.md"):
            name = file.stem.replace("AGENTS.", "")
            contexts.append(name)

        return sorted(contexts)

    def _detect_installed_knowledge(self) -> list[str]:
        """Detect currently installed knowledge scopes."""
        knowledge_dir = self.opencode_dir / "knowledge"
        if not knowledge_dir.exists():
            return []

        scopes = []
        for scope_dir in knowledge_dir.iterdir():
            if scope_dir.is_dir():
                scopes.append(scope_dir.name)

        return sorted(scopes)

    def _detect_installed_skills(self) -> list[str]:
        """Detect currently installed skills."""
        skills_dir = self.opencode_dir / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skills.append(skill_dir.name)

        return sorted(skills)
