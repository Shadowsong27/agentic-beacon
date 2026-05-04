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
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.scanner.scanner import scan_file_for_knowledge


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


@dataclass(frozen=True)
class ResolutionFailure:
    """Structured failure when dependency resolution finds missing deps."""

    errors: list[str]


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

    explicit_contexts = frozenset(beacon.artifacts.contexts)
    explicit_skills = frozenset(beacon.artifacts.skills)

    effective_contexts: set[str] = set(explicit_contexts)
    effective_skills: set[str] = set(explicit_skills)

    # Phase 1: Walk skills (6.4)
    skills_to_walk = list(effective_skills)
    for skill_name in skills_to_walk:
        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
        if not skill_path.exists():
            error_set.add(f"Skill '{skill_name}' not found in warehouse: {skill_path}")
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

        effective_contexts.update(skill_fm.requires.contexts)

    # Phase 3: Validate all effective artifacts exist in warehouse (6.6)
    for ctx_name in effective_contexts:
        ctx_path = warehouse / "contexts" / f"{ctx_name}.md"
        if not ctx_path.exists():
            error_set.add(f"Context '{ctx_name}' not found in warehouse: {ctx_path}")

    for skill_name in effective_skills:
        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
        if not skill_path.exists():
            error_set.add(f"Skill '{skill_name}' not found in warehouse: {skill_path}")

    if error_set:
        return ResolutionFailure(errors=sorted(error_set))

    # Phase 4: Scan all contexts and skills for knowledge references (6.5)
    knowledge: set[str] = set()
    for ctx_name in effective_contexts:
        ctx_path = warehouse / "contexts" / f"{ctx_name}.md"
        knowledge.update(scan_file_for_knowledge(ctx_path, warehouse))

    for skill_name in effective_skills:
        skill_path = warehouse / "skills" / skill_name / "SKILL.md"
        knowledge.update(scan_file_for_knowledge(skill_path, warehouse))

    return EffectiveSet(
        contexts=frozenset(effective_contexts),
        skills=frozenset(effective_skills),
        knowledge=frozenset(knowledge),
        explicit_contexts=explicit_contexts,
        explicit_skills=explicit_skills,
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
