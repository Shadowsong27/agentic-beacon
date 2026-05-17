"""Warehouse lint orchestrator for the warehouse-lint-cli-for-ci OpenSpec change.

Provides lint_warehouse() — a single entry-point that validates a warehouse
directory end-to-end by composing existing path-agnostic primitives.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from beacon.core.dependencies.frontmatter import SkillFrontmatter, parse_frontmatter
from beacon.core.dependencies.manifest import (
    AgentManifestError,
    load_agent_manifest,
    validate_agent_frontmatter_clean,
    validate_agents_directory,
    validate_declared_skills,
)
from beacon.core.scanner.scanner import (
    classify_knowledge_ref,
    extract_markdown_links,
    is_absolute_url,
    normalize_link_target,
    resolve_link,
)
from beacon.domains.warehouse.validator import WarehouseValidator


@dataclass(frozen=True)
class LintFinding:
    """A single lint finding scoped to an artifact path."""

    artifact_path: str
    message: str


@dataclass(frozen=True)
class LintReport:
    """Aggregated lint report for a warehouse directory."""

    findings: tuple[LintFinding, ...]

    def __bool__(self) -> bool:
        return bool(self.findings)


def lint_warehouse(warehouse_path: Path) -> LintReport:
    """Validate a warehouse directory end-to-end.

    Calls every rule helper, concatenates findings in fixed order, and
    returns a LintReport. Rule helpers never raise — any exception from a
    primitive is caught and converted to a LintFinding.

    Args:
        warehouse_path: Path to the warehouse directory.

    Returns:
        LintReport with all findings across all rules.
    """
    resolved = Path(warehouse_path).expanduser().resolve()

    findings: list[LintFinding] = []
    findings.extend(_lint_structure(resolved))
    findings.extend(_lint_skill_frontmatter(resolved))
    findings.extend(_lint_skill_requires(resolved))
    findings.extend(_lint_agent_manifest(resolved))
    findings.extend(_lint_agent_frontmatter(resolved))
    findings.extend(_lint_knowledge_links(resolved))

    # Sort by (artifact_path, message) for stable cross-platform ordering
    sorted_findings = sorted(findings, key=lambda f: (f.artifact_path, f.message))
    return LintReport(findings=tuple(sorted_findings))


# ---------------------------------------------------------------------------
# Rule 1: Structure preflight
# ---------------------------------------------------------------------------


def _lint_structure(warehouse_path: Path) -> list[LintFinding]:
    """Validate warehouse directory structure via WarehouseValidator."""
    validator = WarehouseValidator()
    result = validator.validate(warehouse_path)
    if result.valid:
        return []

    findings = []
    for error in result.errors:
        findings.append(LintFinding(artifact_path="<warehouse>", message=error))
    return findings


# ---------------------------------------------------------------------------
# Rule 2: Skill frontmatter
# ---------------------------------------------------------------------------


def _lint_skill_frontmatter(warehouse_path: Path) -> list[LintFinding]:
    """Validate YAML frontmatter for every skills/*/SKILL.md."""
    skills_dir = warehouse_path / "skills"
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []

    findings = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        relative_path = f"skills/{skill_dir.name}/SKILL.md"
        result = parse_frontmatter(skill_file)

        if not result.success:
            findings.append(
                LintFinding(artifact_path=relative_path, message=result.message)
            )
            continue

        # Validate against SkillFrontmatter schema
        try:
            SkillFrontmatter(**result.data)
        except ValidationError as exc:
            for error in exc.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                msg = f"{field_path}: {error['msg']}" if field_path else error["msg"]
                findings.append(LintFinding(artifact_path=relative_path, message=msg))

    return findings


# ---------------------------------------------------------------------------
# Rule 3: Skill requires.contexts resolution
# ---------------------------------------------------------------------------


def _lint_skill_requires(warehouse_path: Path) -> list[LintFinding]:
    """Verify that every context in requires.contexts exists as contexts/<name>.md."""
    skills_dir = warehouse_path / "skills"
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []

    findings = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        relative_path = f"skills/{skill_dir.name}/SKILL.md"
        result = parse_frontmatter(skill_file)

        # Skip skills whose frontmatter is invalid — rule 2 handles those
        if not result.success:
            continue

        try:
            fm = SkillFrontmatter(**result.data)
        except ValidationError:
            # Invalid schema — rule 2 already handles this
            continue

        for ctx_name in fm.requires.contexts:
            ctx_path = warehouse_path / "contexts" / f"{ctx_name}.md"
            if not ctx_path.exists() or not ctx_path.is_file():
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=(
                            f"requires context '{ctx_name}' but "
                            f"contexts/{ctx_name}.md does not exist"
                        ),
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# Rule 4: Agent manifest
# ---------------------------------------------------------------------------


def _extract_path_from_manifest_error(message: str) -> str:
    """Try to extract an agent path from a manifest error message.

    Returns 'agents/agents.yaml' if no specific agent path is found.
    """
    import re

    # Match patterns like 'agents/foo.md' or 'Agent file agents/foo.md'
    match = re.search(r"agents/([^/\s]+\.md)", message)
    if match:
        return f"agents/{match.group(1)}"
    return "agents/agents.yaml"


def _lint_agent_manifest(warehouse_path: Path) -> list[LintFinding]:
    """Validate agent manifest and run downstream manifest validators."""
    findings = []

    # Attempt to load the manifest; on failure, record findings and return early
    try:
        manifest = load_agent_manifest(warehouse_path)
    except AgentManifestError as exc:
        for line in str(exc).split("\n"):
            line = line.strip()
            if line:
                findings.append(
                    LintFinding(artifact_path="agents/agents.yaml", message=line)
                )
        return findings

    # Manifest loaded (possibly None if agents.yaml absent) — run downstream validators
    try:
        validate_agents_directory(warehouse_path, manifest)
    except AgentManifestError as exc:
        for line in str(exc).split("\n"):
            line = line.strip()
            if line:
                artifact_path = _extract_path_from_manifest_error(line)
                findings.append(LintFinding(artifact_path=artifact_path, message=line))

    try:
        validate_agent_frontmatter_clean(warehouse_path)
    except AgentManifestError as exc:
        for line in str(exc).split("\n"):
            line = line.strip()
            if line:
                artifact_path = _extract_path_from_manifest_error(line)
                findings.append(LintFinding(artifact_path=artifact_path, message=line))

    if manifest is not None:
        try:
            validate_declared_skills(warehouse_path, manifest)
        except AgentManifestError as exc:
            for line in str(exc).split("\n"):
                line = line.strip()
                if line:
                    artifact_path = _extract_path_from_manifest_error(line)
                    findings.append(
                        LintFinding(artifact_path=artifact_path, message=line)
                    )

    return findings


# ---------------------------------------------------------------------------
# Rule 5: Agent frontmatter (name + description)
# ---------------------------------------------------------------------------


def _lint_agent_frontmatter(warehouse_path: Path) -> list[LintFinding]:
    """Require name: and description: in every agents/*.md (excluding README.md)."""
    agents_dir = warehouse_path / "agents"
    if not agents_dir.exists() or not agents_dir.is_dir():
        return []

    findings = []
    for agent_file in sorted(agents_dir.iterdir()):
        if not agent_file.is_file() or agent_file.suffix != ".md":
            continue
        if agent_file.name == "README.md":
            continue

        relative_path = f"agents/{agent_file.name}"
        result = parse_frontmatter(agent_file)

        if not result.success:
            # When frontmatter is wholly absent/malformed, emit ONE finding only
            findings.append(
                LintFinding(artifact_path=relative_path, message=result.message)
            )
            continue

        # Check for required keys
        data = result.data or {}
        for key in ("name", "description"):
            if key not in data:
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=f"missing required key `{key}` in frontmatter",
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# Rule 6: Knowledge link integrity
# ---------------------------------------------------------------------------


def _lint_knowledge_links(warehouse_path: Path) -> list[LintFinding]:
    """Promote broken knowledge links to errors (without modifying scan_file_for_knowledge)."""
    files_to_scan: list[tuple[Path, str]] = []

    # Scan contexts/*.md
    contexts_dir = warehouse_path / "contexts"
    if contexts_dir.exists() and contexts_dir.is_dir():
        for f in sorted(contexts_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                files_to_scan.append((f, f"contexts/{f.name}"))

    # Scan skills/*/SKILL.md
    skills_dir = warehouse_path / "skills"
    if skills_dir.exists() and skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    files_to_scan.append(
                        (skill_file, f"skills/{skill_dir.name}/SKILL.md")
                    )

    findings = []
    for file_path, relative_path in files_to_scan:
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            findings.append(
                LintFinding(
                    artifact_path=relative_path,
                    message=f"could not read file: {file_path}",
                )
            )
            continue

        links = extract_markdown_links(content)
        for link in links:
            raw_target = link.target
            normalized = normalize_link_target(raw_target)
            if not normalized or is_absolute_url(normalized):
                continue

            resolved = resolve_link(file_path, normalized, warehouse_path)
            if resolved is None:
                continue

            resolved_abs = warehouse_path / resolved.warehouse_relative
            if classify_knowledge_ref(resolved_abs, warehouse_path):
                if not resolved_abs.exists():
                    findings.append(
                        LintFinding(
                            artifact_path=relative_path,
                            message=(
                                f"broken knowledge link: {raw_target} → "
                                f"{resolved.warehouse_relative} (file not found)"
                            ),
                        )
                    )

    return findings
