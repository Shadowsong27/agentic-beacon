"""Dependency resolver for computing effective artifact sets.

Composes frontmatter parsing and knowledge scanning to produce the full set of
contexts, skills, and knowledge that should be present after sync, including
transitively-required dependencies.
"""

from dataclasses import dataclass
from pathlib import Path

from beacon.core.dependencies.frontmatter import (
    SkillFrontmatter,
    parse_frontmatter,
)
from beacon.core.dependencies.manifest import (
    AgentManifest,
    load_agent_manifest,
)
from beacon.core.exceptions import ValidationError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.scanner.scanner import scan_file_for_knowledge

MIGRATION_DOC_URL = "docs/migrations/artifact-dependencies-frontmatter.md"


@dataclass(frozen=True)
class SkillGap:
    """Structured gap when a declared agent's required skill is missing."""

    requiring_agent: str
    missing_skill: str
    warehouse_skill_path: str


@dataclass(frozen=True)
class EffectiveSet:
    """Deterministic, idempotent effective artifact set for a project.

    All fields are frozensets for immutability and hashability.
    """

    contexts: frozenset[str]
    skills: frozenset[str]
    knowledge: frozenset[str]
    explicit_contexts: frozenset[str]
    explicit_skills: frozenset[str]
    skill_provenance: dict[str, frozenset[str]]


@dataclass(frozen=True)
class ResolutionFailure:
    """Structured failure when dependency resolution finds missing deps."""

    errors: list[str]
    gaps: list[SkillGap] | None = None


def _agent_name_from_path(path: str) -> str:
    """Extract agent name from a beacon.yaml agent path.

    Handles both 'agents/name.md' and bare 'name.md' forms.
    """
    if path.startswith("agents/"):
        path = path[7:]
    if path.endswith(".md"):
        path = path[:-3]
    return path


def validate_declared_agents_in_manifest(
    beacon: BeaconManifest, agent_manifest: AgentManifest | None
) -> None:
    """Validate that every path in artifacts.agents has a key in agents.yaml.

    Args:
        beacon: Loaded beacon manifest.
        agent_manifest: Loaded agent manifest, or None if absent.

    Raises:
        ValidationError: If any declared agent is missing from the manifest.
    """
    declared = beacon.artifacts.agents
    if not declared:
        return

    if agent_manifest is None:
        raise ValidationError(
            f"Project declares {len(declared)} agent(s) but agents/agents.yaml "
            f"is missing. See {MIGRATION_DOC_URL} for migration instructions."
        )

    missing: list[str] = []
    for path in declared:
        name = _agent_name_from_path(path)
        if name not in agent_manifest.agents:
            missing.append(path)

    if missing:
        raise ValidationError(
            f"Declared agent(s) not found in agents/agents.yaml: {', '.join(missing)}. "
            f"See {MIGRATION_DOC_URL} for migration instructions."
        )


def compute_effective_set(
    beacon: BeaconManifest, warehouse: Path
) -> EffectiveSet | ResolutionFailure:
    """Compute the effective set of artifacts for a project.

    Walks adopted skills to transitively include required contexts,
    then scans all contexts and skills for knowledge references.

    Args:
        beacon: Loaded beacon manifest.
        warehouse: Absolute path to the warehouse root.

    Returns:
        EffectiveSet on success, or ResolutionFailure with collected errors.
    """
    warehouse = warehouse.resolve()
    error_set: set[str] = set()
    gaps: list[SkillGap] = []

    explicit_contexts = frozenset(beacon.artifacts.contexts)
    explicit_skills = frozenset(beacon.artifacts.skills)

    effective_contexts: set[str] = set(explicit_contexts)
    effective_skills: set[str] = set(explicit_skills)

    context_required_by: dict[str, list[str]] = {}
    skill_provenance: dict[str, set[str]] = {}

    # Record explicit provenance for all explicitly declared skills
    for skill_name in explicit_skills:
        skill_provenance.setdefault(skill_name, set()).add("explicit")

    # Phase 0: Resolve declared agents' required skills
    agent_manifest = load_agent_manifest(warehouse)
    if beacon.artifacts.agents:
        if agent_manifest is None:
            error_set.add(
                f"Project declares {len(beacon.artifacts.agents)} agent(s) but "
                f"agents/agents.yaml is missing in {warehouse / 'agents'}."
            )
        else:
            for agent_path in beacon.artifacts.agents:
                agent_name = _agent_name_from_path(agent_path)
                if agent_name not in agent_manifest.agents:
                    error_set.add(
                        f"Declared agent '{agent_path}' not found in "
                        f"agents/agents.yaml. See {MIGRATION_DOC_URL} for migration instructions."
                    )
                    continue

                entry = agent_manifest.agents[agent_name]
                for skill_name in entry.skills:
                    effective_skills.add(skill_name)
                    skill_provenance.setdefault(skill_name, set()).add(
                        f"required-by-agent:{agent_name}"
                    )
                    # Gap: skill required by agent but not declared in beacon.yaml
                    if skill_name not in explicit_skills:
                        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
                        gaps.append(
                            SkillGap(
                                requiring_agent=agent_name,
                                missing_skill=skill_name,
                                warehouse_skill_path=str(skill_path),
                            )
                        )

    # Phase 1: Walk skills (6.4)
    skills_to_walk = list(effective_skills)
    for skill_name in skills_to_walk:
        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
        if not skill_path.exists():
            # Only add error if this skill wasn't already flagged as a gap
            if not any(g.missing_skill == skill_name for g in gaps):
                error_set.add(
                    f"Skill '{skill_name}' not found in warehouse: {skill_path}"
                )
            continue

        result = parse_frontmatter(skill_path)
        if not result.success:
            error_set.add(f"Skill '{skill_name}' frontmatter error: {result.message}")
            continue

        try:
            skill_fm = SkillFrontmatter.model_validate(result.data)
        except Exception as exc:
            error_set.add(f"Skill '{skill_name}' frontmatter validation failed: {exc}")
            continue

        for ctx_name in skill_fm.requires.contexts:
            effective_contexts.add(ctx_name)
            context_required_by.setdefault(ctx_name, []).append(skill_name)

    # Phase 3: Validate all effective artifacts exist in warehouse (6.6)
    for ctx_name in effective_contexts:
        ctx_path = warehouse / "contexts" / f"{ctx_name}.md"
        if not ctx_path.exists():
            if ctx_name in context_required_by:
                skills = ", ".join(context_required_by[ctx_name])
                error_set.add(
                    f"Skill(s) '{skills}' require context '{ctx_name}' "
                    f"which is not found in the warehouse: {ctx_path}"
                )
            else:
                error_set.add(
                    f"Context '{ctx_name}' not found in warehouse: {ctx_path}"
                )

    for skill_name in effective_skills:
        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
        if not skill_path.exists():
            # Only add error if this skill wasn't already flagged as a gap
            if not any(g.missing_skill == skill_name for g in gaps):
                error_set.add(
                    f"Skill '{skill_name}' not found in warehouse: {skill_path}"
                )

    if error_set:
        return ResolutionFailure(errors=sorted(error_set), gaps=gaps or None)

    if gaps:
        return ResolutionFailure(errors=[], gaps=gaps)

    # Phase 4: Scan all contexts and skills for knowledge references (6.5)
    knowledge: set[str] = set()
    for ctx_name in effective_contexts:
        ctx_path = warehouse / "contexts" / f"{ctx_name}.md"
        knowledge.update(scan_file_for_knowledge(ctx_path, warehouse))

    for skill_name in effective_skills:
        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
        knowledge.update(scan_file_for_knowledge(skill_path, warehouse))

    # Build frozen provenance dict
    frozen_provenance = {
        skill: frozenset(prov) for skill, prov in sorted(skill_provenance.items())
    }

    return EffectiveSet(
        contexts=frozenset(effective_contexts),
        skills=frozenset(effective_skills),
        knowledge=frozenset(knowledge),
        explicit_contexts=explicit_contexts,
        explicit_skills=explicit_skills,
        skill_provenance=frozen_provenance,
    )


def is_transitively_required(artifact: str, effective_set: EffectiveSet) -> bool:
    """Return True if an artifact is in the effective set only transitively.

    An artifact is transitively required if it appears in the effective
    contexts or skills but was not explicitly adopted in beacon.yaml.

    Args:
        artifact: Artifact name (context stem or skill directory name).
        effective_set: The computed effective set.

    Returns:
        True if the artifact is transitively required.
    """
    in_contexts = artifact in effective_set.contexts
    in_explicit_contexts = artifact in effective_set.explicit_contexts
    in_skills = artifact in effective_set.skills
    in_explicit_skills = artifact in effective_set.explicit_skills

    context_transitive = in_contexts and not in_explicit_contexts
    skill_transitive = in_skills and not in_explicit_skills

    return context_transitive or skill_transitive
