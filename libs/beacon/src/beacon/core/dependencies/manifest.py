"""Agent manifest model and validators for the warehouse agents directory.

Implements the move-agent-requires-to-warehouse-manifest OpenSpec change.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from beacon.core.dependencies.frontmatter import parse_frontmatter
from beacon.core.exceptions import AgentManifestError

MIGRATION_DOC_URL = "docs/migrations/artifact-dependencies-frontmatter.md"


class AgentEntry(BaseModel):
    """A single agent entry in the agent manifest."""

    model_config = ConfigDict(extra="allow")

    skills: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reject_contexts_and_coerce_skills(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        if "contexts" in data:
            raise ValueError(
                "'contexts' is not allowed at the agent entry level. "
                f"See {MIGRATION_DOC_URL} for migration instructions."
            )
        skills = data.get("skills")
        if skills is None:
            data["skills"] = []
        elif not isinstance(skills, list):
            raise ValueError("skills must be a list")
        return data


class AgentManifest(BaseModel):
    """Top-level agent manifest mapping agent names to their entries."""

    model_config = ConfigDict(extra="forbid")

    agents: dict[str, AgentEntry] = Field(default_factory=dict)


def load_agent_manifest(warehouse_path: Path) -> AgentManifest | None:
    """Load the agent manifest from agents/agents.yaml.

    Args:
        warehouse_path: Root of the warehouse clone.

    Returns:
        AgentManifest on success, or None if agents/agents.yaml is absent.

    Raises:
        AgentManifestError: On YAML parse failure or schema validation failure.
    """
    manifest_path = warehouse_path / "agents" / "agents.yaml"
    if not manifest_path.exists():
        return None

    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AgentManifestError(
            f"Failed to parse agents/agents.yaml: {exc}\n"
            f"See {MIGRATION_DOC_URL} for migration instructions."
        ) from exc
    except OSError as exc:
        raise AgentManifestError(
            f"Failed to read agents/agents.yaml: {exc}\n"
            f"See {MIGRATION_DOC_URL} for migration instructions."
        ) from exc

    if raw is None:
        raw = {}

    if not isinstance(raw, dict):
        raise AgentManifestError(
            f"agents/agents.yaml must be a YAML mapping (dict), got {type(raw).__name__}.\n"
            f"See {MIGRATION_DOC_URL} for migration instructions."
        )

    try:
        manifest = AgentManifest(agents=raw)
    except Exception as exc:
        raise AgentManifestError(
            f"agents/agents.yaml schema validation failed: {exc}\n"
            f"See {MIGRATION_DOC_URL} for migration instructions."
        ) from exc

    return manifest


def validate_agents_directory(
    warehouse_path: Path, manifest: AgentManifest | None
) -> None:
    """Check bidirectional correspondence between agents/*.md and manifest keys.

    Every agent file (excluding README.md) must have a matching manifest entry,
    and every manifest entry must have a matching agent file.

    Args:
        warehouse_path: Root of the warehouse clone.
        manifest: Loaded agent manifest, or None if absent.

    Raises:
        AgentManifestError: On any mismatch.
    """
    agents_dir = warehouse_path / "agents"
    if not agents_dir.exists():
        return

    md_files = {
        f.stem
        for f in agents_dir.iterdir()
        if f.is_file() and f.suffix == ".md" and f.name != "README.md"
    }

    manifest_keys = set(manifest.agents.keys()) if manifest else set()

    missing_in_manifest = md_files - manifest_keys
    orphan_in_manifest = manifest_keys - md_files

    errors = []
    if missing_in_manifest:
        for name in sorted(missing_in_manifest):
            errors.append(
                f"Agent file agents/{name}.md has no entry in agents/agents.yaml. "
                f"See {MIGRATION_DOC_URL} for migration instructions."
            )
    if orphan_in_manifest:
        for name in sorted(orphan_in_manifest):
            errors.append(
                f"agents/agents.yaml declares agent '{name}' but agents/{name}.md does not exist. "
                f"See {MIGRATION_DOC_URL} for migration instructions."
            )

    if errors:
        raise AgentManifestError("\n".join(errors))


def validate_agent_frontmatter_clean(warehouse_path: Path) -> None:
    """Assert that no agents/*.md file contains a 'requires:' key in frontmatter.

    Args:
        warehouse_path: Root of the warehouse clone.

    Raises:
        AgentManifestError: If any agent file still has requires: frontmatter.
    """
    agents_dir = warehouse_path / "agents"
    if not agents_dir.exists():
        return

    errors = []
    for f in sorted(agents_dir.iterdir()):
        if not f.is_file() or f.suffix != ".md" or f.name == "README.md":
            continue

        result = parse_frontmatter(f)
        if not result.success:
            # If frontmatter is missing/unreadable, that's fine for this check
            continue

        if result.data and "requires" in result.data:
            errors.append(
                f"agents/{f.name} still contains 'requires:' in frontmatter. "
                f"Move dependencies to agents/agents.yaml. "
                f"See {MIGRATION_DOC_URL} for migration instructions."
            )

    if errors:
        raise AgentManifestError("\n".join(errors))


def validate_declared_skills(warehouse_path: Path, manifest: AgentManifest) -> None:
    """Assert that every skill declared in the manifest exists in the warehouse.

    Args:
        warehouse_path: Root of the warehouse clone.
        manifest: Loaded agent manifest.

    Raises:
        AgentManifestError: If any declared skill is missing.
    """
    errors = []
    for agent_name, entry in sorted(manifest.agents.items()):
        for skill_name in entry.skills:
            skill_path = warehouse_path / "skills" / skill_name / "SKILL.md"
            if not skill_path.exists():
                errors.append(
                    f"Agent '{agent_name}' declares skill '{skill_name}' "
                    f"but {skill_path} does not exist. "
                    f"See {MIGRATION_DOC_URL} for migration instructions."
                )

    if errors:
        raise AgentManifestError("\n".join(errors))
