"""Unit tests for record-skill's create_skill.py scaffolding script (PER-65).

Tests cover:
- validate_kebab_case: name normalisation
- _build_skill_md: generated SKILL.md content for both paths
- _build_pep723_script: PEP 723 header and template structure
- scaffold_skill: end-to-end file creation for markdown-only and markdown+scripts paths
"""

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the script as a module (it is a PEP 723 standalone script, not a
# package, so we import it via importlib rather than a normal import).
# ---------------------------------------------------------------------------

_SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "beacon"
    / "src"
    / "beacon"
    / "data"
    / "skills"
    / "record-skill"
    / "scripts"
    / "create_skill.py"
)


def _load_create_skill():
    """Load create_skill.py as a module and return it."""
    spec = importlib.util.spec_from_file_location("create_skill", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cs():
    """Return the loaded create_skill module."""
    return _load_create_skill()


# ---------------------------------------------------------------------------
# validate_kebab_case
# ---------------------------------------------------------------------------


class TestValidateKebabCase:
    def test_already_kebab(self, cs):
        assert cs.validate_kebab_case("my-skill") == "my-skill"

    def test_spaces_become_hyphens(self, cs):
        assert cs.validate_kebab_case("my skill") == "my-skill"

    def test_underscores_become_hyphens(self, cs):
        assert cs.validate_kebab_case("my_skill") == "my-skill"

    def test_uppercase_lowercased(self, cs):
        assert cs.validate_kebab_case("MySkill") == "myskill"

    def test_special_chars_removed(self, cs):
        assert cs.validate_kebab_case("my@skill!") == "myskill"

    def test_multiple_hyphens_collapsed(self, cs):
        assert cs.validate_kebab_case("my--skill") == "my-skill"

    def test_leading_trailing_hyphens_stripped(self, cs):
        assert cs.validate_kebab_case("-my-skill-") == "my-skill"

    def test_mixed_normalisation(self, cs):
        assert cs.validate_kebab_case("My_Cool Skill!") == "my-cool-skill"


# ---------------------------------------------------------------------------
# _build_skill_md
# ---------------------------------------------------------------------------


class TestBuildSkillMd:
    def test_contains_frontmatter_name(self, cs):
        content = cs._build_skill_md(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        assert "name: deploy-check" in content

    def test_contains_frontmatter_description(self, cs):
        content = cs._build_skill_md(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        assert "description: Validate deployment" in content

    def test_frontmatter_has_license_and_compatibility(self, cs):
        content = cs._build_skill_md(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        assert "license: MIT" in content
        assert "compatibility: opencode" in content

    def test_contains_invocation(self, cs):
        content = cs._build_skill_md(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        assert "/deploy-check" in content

    def test_standard_sections_present(self, cs):
        content = cs._build_skill_md(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        assert "## Purpose" in content
        assert "## When to Use" in content
        assert "## Invocation" in content
        assert "## Process" in content
        assert "## Examples" in content
        assert "## Checklist" in content

    def test_no_scripts_section_when_not_requested(self, cs):
        content = cs._build_skill_md(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        assert "## Scripts" not in content

    def test_scripts_section_present_when_requested(self, cs):
        content = cs._build_skill_md(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )
        assert "## Scripts" in content

    def test_scripts_section_references_skill_name(self, cs):
        content = cs._build_skill_md(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )
        assert "s3-cleanup.py" in content

    def test_scripts_section_uses_skill_dir_var(self, cs):
        content = cs._build_skill_md(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )
        assert "${SKILL_DIR}" in content


# ---------------------------------------------------------------------------
# _build_pep723_script
# ---------------------------------------------------------------------------


class TestBuildPep723Script:
    def test_has_pep723_header(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert "# /// script" in content

    def test_has_requires_python(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert "requires-python" in content

    def test_has_dependencies_field(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert "dependencies" in content

    def test_has_closing_marker(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert "# ///" in content

    def test_has_main_function(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert "def main()" in content

    def test_has_dunder_main_guard(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert '__name__ == "__main__"' in content

    def test_description_in_docstring(self, cs):
        content = cs._build_pep723_script("s3-cleanup", "Clean S3 buckets")
        assert "Clean S3 buckets" in content


# ---------------------------------------------------------------------------
# scaffold_skill: markdown-only path
# ---------------------------------------------------------------------------


class TestScaffoldSkillMarkdownOnly:
    def test_creates_skill_directory(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )

        assert skill_dir.exists()
        assert skill_dir.is_dir()

    def test_skill_directory_name_matches(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )

        assert skill_dir.name == "deploy-check"

    def test_skill_md_is_created(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )

        assert (skill_dir / "SKILL.md").exists()

    def test_skill_md_has_correct_frontmatter(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )
        content = (skill_dir / "SKILL.md").read_text()

        assert "name: deploy-check" in content
        assert "description: Validate deployment" in content

    def test_no_scripts_directory_created(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )

        assert not (skill_dir / "scripts").exists()

    def test_returns_path_under_artifacts_skills(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "deploy-check", "Validate deployment", "/deploy-check", False
        )

        assert skill_dir == artifacts_dir / "skills" / "deploy-check"


# ---------------------------------------------------------------------------
# scaffold_skill: markdown + scripts path
# ---------------------------------------------------------------------------


class TestScaffoldSkillWithScript:
    def test_creates_scripts_directory(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )

        assert (skill_dir / "scripts").exists()
        assert (skill_dir / "scripts").is_dir()

    def test_creates_python_script(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )

        assert (skill_dir / "scripts" / "s3-cleanup.py").exists()

    def test_script_has_pep723_header(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )
        script_content = (skill_dir / "scripts" / "s3-cleanup.py").read_text()

        assert "# /// script" in script_content
        assert "requires-python" in script_content
        assert "dependencies" in script_content

    def test_script_named_after_skill(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )

        assert (skill_dir / "scripts" / "s3-cleanup.py").exists()

    def test_skill_md_references_script(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )
        content = (skill_dir / "SKILL.md").read_text()

        assert "s3-cleanup.py" in content

    def test_both_skill_md_and_script_exist(self, cs, tmp_path, monkeypatch):
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        skill_dir = cs.scaffold_skill(
            "s3-cleanup", "Clean S3 buckets", "/s3-cleanup", True
        )

        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "scripts" / "s3-cleanup.py").exists()


# ---------------------------------------------------------------------------
# scaffold_skill: error cases
# ---------------------------------------------------------------------------


class TestScaffoldSkillErrorCases:
    def test_exits_when_no_artifacts_dir(self, cs, tmp_path, monkeypatch):
        """scaffold_skill calls sys.exit(1) when .agentic-beacon/artifacts/ is absent."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            cs.scaffold_skill("new-skill", "A new skill", "/new-skill", False)

        assert exc_info.value.code == 1

    def test_exits_when_skill_already_exists(self, cs, tmp_path, monkeypatch):
        """scaffold_skill calls sys.exit(1) when the target skill dir already exists."""
        artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)
        existing = artifacts_dir / "skills" / "dup-skill"
        existing.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            cs.scaffold_skill("dup-skill", "Duplicate skill", "/dup-skill", False)

        assert exc_info.value.code == 1
