# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Interactive scaffolding for new Beacon skills.

Creates a new skill directory under .agentic-beacon/artifacts/skills/<name>/
with proper frontmatter, section structure, and optional PEP 723 Python script.
"""

import re
import sys
from pathlib import Path


def prompt(text: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        raw = input(f"{text} [{default}]: ").strip()
        return raw if raw else default
    while True:
        raw = input(f"{text}: ").strip()
        if raw:
            return raw
        print("  (required)")


def prompt_yes_no(text: str, default: bool = False) -> bool:
    """Prompt for yes/no with optional default."""
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        raw = input(f"{text}{suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please enter 'y' or 'n'")


def validate_kebab_case(name: str) -> str:
    """Validate and convert to kebab-case."""
    # Replace underscores and spaces with hyphens
    normalized = name.replace("_", "-").replace(" ", "-").lower()
    # Remove any non-alphanumeric-non-hyphen characters
    normalized = re.sub(r"[^a-z0-9-]", "", normalized)
    # Collapse multiple hyphens
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


def scaffold_skill(
    name: str,
    description: str,
    invocation: str,
    include_scripts: bool,
) -> Path:
    """Scaffold a new skill directory and return its path."""
    project_root = Path.cwd()
    artifacts_dir = project_root / ".agentic-beacon" / "artifacts"
    if not artifacts_dir.exists():
        print("Error: No .agentic-beacon/artifacts/ directory found.")
        print("Run 'abc sync' or 'abc setup' first.")
        sys.exit(1)

    skill_dir = artifacts_dir / "skills" / name
    if skill_dir.exists():
        print(f"Error: Skill directory already exists: {skill_dir}")
        sys.exit(1)

    skill_dir.mkdir(parents=True)

    # Write SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(_build_skill_md(name, description, invocation, include_scripts))

    # Write optional PEP 723 script
    if include_scripts:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / f"{name}.py"
        script_file.write_text(_build_pep723_script(name, description))

    return skill_dir


def _build_skill_md(
    name: str, description: str, invocation: str, include_scripts: bool
) -> str:
    """Build the SKILL.md content."""
    scripts_section = ""
    if include_scripts:
        scripts_section = f"""
## Scripts

| Script | Purpose |
|--------|---------|
| `${{SKILL_DIR}}/scripts/{name}.py` | Main executable script |

"""

    return f"""---
name: {name}
description: {description}
license: MIT
compatibility: opencode
---

# SKILL: {name.replace("-", " ").title()}

## Purpose

{description}

## When to Use

<!-- Describe the specific situations where this skill applies -->

## Invocation

```
{invocation}
```

{scripts_section}## Process

<!-- Step-by-step workflow -->

## Examples

<!-- Concrete usage examples -->

## Checklist

- [ ] Skill files are complete and tested
- [ ] All scripts run without errors (`uv run ${{SKILL_DIR}}/scripts/*.py`)
- [ ] Documentation is accurate and up-to-date
- [ ] Skill has been validated in a real project
"""


def _build_pep723_script(name: str, description: str) -> str:
    """Build a PEP 723 inline script template."""
    return f'''# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""{description}"""

import sys


def main() -> None:
    """Main entry point for {name}."""
    print(f"Running {{name}}...")
    # TODO: Implement your skill logic here
    pass


if __name__ == "__main__":
    main()
'''


def main() -> None:
    """Run interactive skill scaffolding."""
    print("=" * 60)
    print("Beacon Skill Scaffolder")
    print("=" * 60)
    print()

    name_raw = prompt("Skill name (kebab-case)")
    name = validate_kebab_case(name_raw)
    if name != name_raw:
        print(f"  → Normalized to: {name}")

    description = prompt("One-line description")
    invocation = prompt("Invocation form", default=f"/{name}")
    include_scripts = prompt_yes_no("Include PEP 723 Python script", default=False)

    print()
    print("Scaffolding...")

    skill_dir = scaffold_skill(name, description, invocation, include_scripts)

    print()
    print("=" * 60)
    print(f"✓ Created skill: {name}")
    print("=" * 60)
    print()
    print(f"  Location: {skill_dir}")
    print(f"  SKILL.md: {skill_dir / 'SKILL.md'}")
    if include_scripts:
        print(f"  Script:   {skill_dir / 'scripts' / f'{name}.py'}")
    print()
    print("Next steps:")
    print(f"  1. Edit {skill_dir / 'SKILL.md'} to fill in Process and Examples")
    if include_scripts:
        print(f"  2. Implement logic in {skill_dir / 'scripts' / f'{name}.py'}")
        print(f"  3. Test: uv run {skill_dir / 'scripts' / f'{name}.py'}")
    print(f"  4. Add to beacon.yaml: skills/{name}/")
    print("  5. Run 'abc sync' to distribute")
    print()


if __name__ == "__main__":
    main()
