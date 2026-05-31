"""Warehouse lint orchestrator for the warehouse-lint-cli-for-ci OpenSpec change.

Provides lint_warehouse() — a single entry-point that validates a warehouse
directory end-to-end by composing existing path-agnostic primitives.
"""

from __future__ import annotations

import re
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
    LINK_ABSOLUTE_URL,
    LINK_CANONICAL,
    LINK_CROSS_ARTIFACT_RELATIVE,
    LINK_OWN_SKILL_FOLDER,
    LINK_WAREHOUSE_ESCAPE,
    classify_link,
    extract_markdown_headings,
    extract_markdown_links,
    resolve_canonical_link,
    slugify_heading,
    to_canonical,
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
    rewritten_links: int = 0
    files_touched: int = 0
    fix_requested: bool = False

    def __bool__(self) -> bool:
        return bool(self.findings)


def lint_warehouse(warehouse_path: Path, *, fix: bool = False) -> LintReport:
    """Validate a warehouse directory end-to-end."""
    resolved = Path(warehouse_path).expanduser().resolve()
    rewritten_links = 0
    files_touched = 0
    if fix:
        rewritten_links, files_touched = _fix_artifact_links(resolved)

    findings: list[LintFinding] = []
    findings.extend(_lint_structure(resolved))
    findings.extend(_lint_skill_frontmatter(resolved))
    findings.extend(_lint_skill_requires(resolved))
    findings.extend(_lint_agent_manifest(resolved))
    findings.extend(_lint_agent_frontmatter(resolved))
    findings.extend(_lint_artifact_links(resolved))

    sorted_findings = sorted(findings, key=lambda f: (f.artifact_path, f.message))
    return LintReport(
        findings=tuple(sorted_findings),
        rewritten_links=rewritten_links,
        files_touched=files_touched,
        fix_requested=fix,
    )


def _iter_artifact_markdown_files(warehouse_path: Path) -> list[tuple[Path, str]]:
    """Return every markdown artifact path covered by the artifact-link lint."""
    files_to_scan: list[tuple[Path, str]] = []

    contexts_dir = warehouse_path / "contexts"
    if contexts_dir.exists() and contexts_dir.is_dir():
        for file_path in sorted(contexts_dir.iterdir()):
            if file_path.is_file() and file_path.suffix == ".md":
                files_to_scan.append((file_path, f"contexts/{file_path.name}"))

    skills_dir = warehouse_path / "skills"
    if skills_dir.exists() and skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                files_to_scan.append((skill_file, f"skills/{skill_dir.name}/SKILL.md"))

    agents_dir = warehouse_path / "agents"
    if agents_dir.exists() and agents_dir.is_dir():
        for file_path in sorted(agents_dir.iterdir()):
            if (
                file_path.is_file()
                and file_path.suffix == ".md"
                and file_path.name != "README.md"
            ):
                files_to_scan.append((file_path, f"agents/{file_path.name}"))

    knowledge_dir = warehouse_path / "knowledge"
    if knowledge_dir.exists() and knowledge_dir.is_dir():
        for file_path in sorted(knowledge_dir.rglob("*.md")):
            if file_path.is_file():
                files_to_scan.append(
                    (file_path, file_path.relative_to(warehouse_path).as_posix())
                )

    # agent-partials/ is a first-class artifact family in the Phase 4 layout
    # — partial bodies (e.g. agent-partials/deep-review-checklist.md) are
    # mirrored into projects and may themselves contain canonical links
    # back to other artifacts. Scan them under the same rules so a malformed
    # cross-artifact link inside a shared partial does not slip past lint
    # and get distributed to every project that pulls the partial.
    agent_partials_dir = warehouse_path / "agent-partials"
    if agent_partials_dir.exists() and agent_partials_dir.is_dir():
        for file_path in sorted(agent_partials_dir.rglob("*.md")):
            if file_path.is_file():
                files_to_scan.append(
                    (file_path, file_path.relative_to(warehouse_path).as_posix())
                )

    return files_to_scan


# ---------------------------------------------------------------------------
# Rule 1: Structure preflight
# ---------------------------------------------------------------------------


def _lint_structure(warehouse_path: Path) -> list[LintFinding]:
    """Validate warehouse directory structure via WarehouseValidator."""
    validator = WarehouseValidator()
    result = validator.validate(warehouse_path, validate_manifest=False)
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
        if not result.success:
            continue

        try:
            fm = SkillFrontmatter(**result.data)
        except ValidationError:
            continue

        for ctx_name in fm.requires.contexts:
            ctx_path = warehouse_path / "contexts" / f"{ctx_name}.md"
            if not ctx_path.exists() or not ctx_path.is_file():
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=(
                            f"requires context '{ctx_name}' but contexts/{ctx_name}.md does not exist"
                        ),
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# Rule 4: Agent manifest
# ---------------------------------------------------------------------------


def _extract_path_from_manifest_error(message: str) -> str:
    """Try to extract an agent path from a manifest error message."""
    match = re.search(r"agents/([^/\s]+\.md)", message)
    if match:
        return f"agents/{match.group(1)}"

    match = re.search(r"""Agent\s+['\"]([^'\"]+)['\"]""", message)
    if match:
        return f"agents/{match.group(1)}.md"

    return "agents/agents.yaml"


def _lint_agent_manifest(warehouse_path: Path) -> list[LintFinding]:
    """Validate agent manifest and run downstream manifest validators."""
    findings = []
    manifest = None
    manifest_parsed = False
    try:
        manifest = load_agent_manifest(warehouse_path)
        manifest_parsed = True
    except AgentManifestError as exc:
        findings.append(
            LintFinding(artifact_path="agents/agents.yaml", message=str(exc).strip())
        )

    if manifest_parsed:
        try:
            validate_agents_directory(warehouse_path, manifest)
        except AgentManifestError as exc:
            for line in str(exc).split("\n"):
                line = line.strip()
                if line:
                    findings.append(
                        LintFinding(
                            artifact_path=_extract_path_from_manifest_error(line),
                            message=line,
                        )
                    )

    try:
        validate_agent_frontmatter_clean(warehouse_path)
    except AgentManifestError as exc:
        for line in str(exc).split("\n"):
            line = line.strip()
            if line:
                findings.append(
                    LintFinding(
                        artifact_path=_extract_path_from_manifest_error(line),
                        message=line,
                    )
                )

    if manifest_parsed and manifest is not None:
        try:
            validate_declared_skills(warehouse_path, manifest)
        except AgentManifestError as exc:
            for line in str(exc).split("\n"):
                line = line.strip()
                if line:
                    findings.append(
                        LintFinding(
                            artifact_path=_extract_path_from_manifest_error(line),
                            message=line,
                        )
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
            findings.append(
                LintFinding(artifact_path=relative_path, message=result.message)
            )
            continue

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
# Rule 6: Artifact link integrity
# ---------------------------------------------------------------------------


def _lint_artifact_links(warehouse_path: Path) -> list[LintFinding]:
    """Validate cross-artifact link integrity without changing sync behavior."""
    findings: list[LintFinding] = []

    for file_path, relative_path in _iter_artifact_markdown_files(warehouse_path):
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

        own_headings = extract_markdown_headings(file_path)
        for link in extract_markdown_links(content):
            raw_target = link.target.strip()
            if not raw_target:
                continue

            if raw_target.startswith("#"):
                anchor = slugify_heading(raw_target[1:])
                if anchor not in own_headings:
                    findings.append(
                        LintFinding(
                            artifact_path=relative_path,
                            message=(
                                f"unresolved anchor: {raw_target} does not match any heading in {relative_path}"
                            ),
                        )
                    )
                continue

            category = classify_link(raw_target, file_path, warehouse_path)
            if category in {LINK_ABSOLUTE_URL, LINK_OWN_SKILL_FOLDER}:
                continue

            if category == LINK_CROSS_ARTIFACT_RELATIVE:
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=(
                            f"malformed cross-artifact link: {raw_target} must use canonical form "
                            f"{to_canonical(raw_target, file_path, warehouse_path)}"
                        ),
                    )
                )
                continue

            if category == LINK_WAREHOUSE_ESCAPE:
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=f"warehouse-escape link: {raw_target} resolves outside the warehouse root",
                    )
                )
                continue

            if category != LINK_CANONICAL:
                continue

            resolved = resolve_canonical_link(raw_target, warehouse_path)
            if resolved is None:
                continue
            target_path, anchor = resolved

            if not target_path.exists():
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=(
                            f"missing canonical target: {raw_target} → {target_path.relative_to(warehouse_path).as_posix()}"
                        ),
                    )
                )
                continue

            if anchor is not None and anchor not in extract_markdown_headings(
                target_path
            ):
                findings.append(
                    LintFinding(
                        artifact_path=relative_path,
                        message=(
                            f"unresolved anchor: {raw_target} does not match any heading in "
                            f"{target_path.relative_to(warehouse_path).as_posix()}"
                        ),
                    )
                )

    return sorted(findings, key=lambda f: (f.artifact_path, f.message))


_INLINE_LINK_RE = re.compile(r"(?<!\\)(?<!!)\[([^\]]*)\]\(([^)]+)\)")


def _fix_artifact_links(warehouse_path: Path) -> tuple[int, int]:
    """Rewrite fixable cross-artifact links in place and report counts.

    Mirrors ``extract_markdown_links`` exactly so ``--fix`` only ever touches
    links that the lint would actually flag: links inside fenced code blocks
    (``` / ~~~) and inline code spans (backticks) are left untouched.
    """
    rewritten_links = 0
    files_touched = 0

    for file_path, _relative_path in _iter_artifact_markdown_files(warehouse_path):
        try:
            original = file_path.read_text(encoding="utf-8")
        except OSError:
            continue

        changed = False

        def replace_link(
            match: re.Match[str], current_file_path: Path = file_path
        ) -> str:
            nonlocal rewritten_links, changed

            full_text = match.group(0)
            target = match.group(2).strip()
            if (
                classify_link(target, current_file_path, warehouse_path)
                != LINK_CROSS_ARTIFACT_RELATIVE
            ):
                return full_text

            changed = True
            rewritten_links += 1
            # Rebuild the link from regex spans so we only ever rewrite the
            # target (group 2), never the label (group 1). A naive
            # ``full_text.replace(group(2), ..., 1)`` corrupts links of the
            # form ``[../../contexts/a.md](../../contexts/a.md)`` — `replace`
            # finds the label text first and rewrites it instead of the
            # destination. Using span slicing relative to the match keeps the
            # label byte-for-byte and only replaces the parenthesised target.
            target_start = match.start(2) - match.start(0)
            target_end = match.end(2) - match.start(0)
            new_target = to_canonical(target, current_file_path, warehouse_path)
            return full_text[:target_start] + new_target + full_text[target_end:]

        out_lines: list[str] = []
        in_code_fence = False
        fence_char: str | None = None
        for line in original.splitlines(keepends=True):
            stripped = line.lstrip()

            # Toggle fenced code block state on ``` or ~~~ at line start.
            if not in_code_fence and (
                stripped.startswith("```") or stripped.startswith("~~~")
            ):
                in_code_fence = True
                fence_char = stripped[:3]
                out_lines.append(line)
                continue
            if (
                in_code_fence
                and fence_char is not None
                and stripped.startswith(fence_char)
            ):
                in_code_fence = False
                fence_char = None
                out_lines.append(line)
                continue
            if in_code_fence:
                out_lines.append(line)
                continue

            # Outside fences: rewrite only the segments outside inline code
            # spans (odd-indexed backtick splits are inside inline code).
            parts = line.split("`")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    parts[i] = _INLINE_LINK_RE.sub(replace_link, part)
            out_lines.append("`".join(parts))

        updated = "".join(out_lines)
        if changed and updated != original:
            file_path.write_text(updated, encoding="utf-8")
            files_touched += 1

    return rewritten_links, files_touched
