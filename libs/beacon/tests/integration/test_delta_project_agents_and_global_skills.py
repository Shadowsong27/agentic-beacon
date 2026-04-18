"""Tests for abc delta project-scoped agent and global skill reminder sections.

Covers:
- _find_project_level_agents: detection of .claude/agents/ and .opencode/agents/
- _find_global_untracked_skills: detection of non-bundled skills in global dirs
- _bundled_skill_names: reads bundled skill names from data/skills/
- Integration: delta output shows/hides each reminder section correctly
- GlobalSettings ignore patterns: skills filtered by fnmatch patterns
"""

from pathlib import Path

import pytest
from beacon.cli import main
from beacon.core.delta import DeltaComparator
from beacon.core.manifest.beacon import BeaconManifest
from beacon.utils.agents import _find_project_level_agents
from beacon.utils.delta import _find_untracked_local_files
from beacon.utils.skills import _bundled_skill_names, _find_global_untracked_skills
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# _find_project_level_agents
# ---------------------------------------------------------------------------


def test_find_project_level_agents_empty_when_no_dirs(tmp_path):
    """No project agent dirs → empty result."""
    assert _find_project_level_agents(tmp_path) == {}


def test_find_project_level_agents_claudecode_only(tmp_path):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "code-reviewer.md").write_text("# Agent\n")
    (agents_dir / "sql-expert.md").write_text("# Agent\n")

    result = _find_project_level_agents(tmp_path)

    assert set(result.keys()) == {"claudecode"}
    assert result["claudecode"] == ["code-reviewer.md", "sql-expert.md"]


def test_find_project_level_agents_opencode_only(tmp_path):
    agents_dir = tmp_path / ".opencode" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "pipeline-dev.md").write_text("# Agent\n")

    result = _find_project_level_agents(tmp_path)

    assert set(result.keys()) == {"opencode"}
    assert result["opencode"] == ["pipeline-dev.md"]


def test_find_project_level_agents_both_tools(tmp_path):
    for tool_dir in [".claude", ".opencode"]:
        agents_dir = tmp_path / tool_dir / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "reviewer.md").write_text("# Agent\n")

    result = _find_project_level_agents(tmp_path)

    assert set(result.keys()) == {"claudecode", "opencode"}
    assert result["claudecode"] == ["reviewer.md"]
    assert result["opencode"] == ["reviewer.md"]


def test_find_project_level_agents_excludes_readme(tmp_path):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "README.md").write_text("# Agents\n")
    (agents_dir / "my-agent.md").write_text("# Agent\n")

    result = _find_project_level_agents(tmp_path)

    assert result["claudecode"] == ["my-agent.md"]


def test_find_project_level_agents_empty_dir_omitted(tmp_path):
    """An existing but empty agents dir should not appear in the result."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)

    result = _find_project_level_agents(tmp_path)

    assert result == {}


def test_find_project_level_agents_returns_sorted(tmp_path):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    for name in ["zebra.md", "alpha.md", "mango.md"]:
        (agents_dir / name).write_text("# Agent\n")

    result = _find_project_level_agents(tmp_path)

    assert result["claudecode"] == ["alpha.md", "mango.md", "zebra.md"]


# ---------------------------------------------------------------------------
# _bundled_skill_names
# ---------------------------------------------------------------------------


def test_bundled_skill_names_returns_set_of_strings():
    names = _bundled_skill_names()
    assert isinstance(names, set)
    # Every entry should be a non-empty string
    for name in names:
        assert isinstance(name, str) and name


def test_bundled_skill_names_matches_data_skills_dir():
    """Bundled names must correspond to directories that actually have a SKILL.md."""
    bundled_dir = (
        Path(__file__).parent.parent.parent / "src" / "beacon" / "data" / "skills"
    )
    if not bundled_dir.exists():
        pytest.skip("data/skills directory not present")
    expected = {
        d.name
        for d in bundled_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }
    assert _bundled_skill_names() == expected


# ---------------------------------------------------------------------------
# _find_global_untracked_skills
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_home_for_skills(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


def test_find_global_untracked_skills_empty_when_no_dirs(isolated_home_for_skills):
    assert _find_global_untracked_skills() == {}


def test_find_global_untracked_skills_claudecode(isolated_home_for_skills):
    skills_dir = isolated_home_for_skills / ".claude" / "skills"
    skill = skills_dir / "my-custom-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Custom\n")

    result = _find_global_untracked_skills()

    assert set(result.keys()) == {"claudecode"}
    assert result["claudecode"] == ["my-custom-skill"]


def test_find_global_untracked_skills_opencode(isolated_home_for_skills):
    skills_dir = isolated_home_for_skills / ".config" / "opencode" / "skills"
    skill = skills_dir / "pipeline-helper"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Helper\n")

    result = _find_global_untracked_skills()

    assert set(result.keys()) == {"opencode"}
    assert result["opencode"] == ["pipeline-helper"]


def test_find_global_untracked_skills_both_tools(isolated_home_for_skills):
    for skills_dir, name in [
        (isolated_home_for_skills / ".claude" / "skills", "sql-tools"),
        (isolated_home_for_skills / ".config" / "opencode" / "skills", "sql-tools"),
    ]:
        skill = skills_dir / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Tool\n")

    result = _find_global_untracked_skills()

    assert set(result.keys()) == {"claudecode", "opencode"}
    assert result["claudecode"] == ["sql-tools"]
    assert result["opencode"] == ["sql-tools"]


def test_find_global_untracked_skills_excludes_bundled(isolated_home_for_skills):
    """Skills whose names match bundled skills must be excluded."""
    bundled = _bundled_skill_names()
    if not bundled:
        pytest.skip("No bundled skills present to test exclusion")

    bundled_name = next(iter(bundled))
    skills_dir = isolated_home_for_skills / ".claude" / "skills" / bundled_name
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Bundled\n")

    result = _find_global_untracked_skills()

    # Bundled skill must not appear
    claudecode_names = result.get("claudecode", [])
    assert bundled_name not in claudecode_names


def test_find_global_untracked_skills_ignores_dirs_without_skill_md(
    isolated_home_for_skills,
):
    """Directories without SKILL.md are not skills and must be ignored."""
    skills_dir = isolated_home_for_skills / ".claude" / "skills" / "not-a-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "README.md").write_text("# Not a skill\n")

    result = _find_global_untracked_skills()

    assert result == {}


def test_find_global_untracked_skills_empty_dir_omitted(isolated_home_for_skills):
    skills_dir = isolated_home_for_skills / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    result = _find_global_untracked_skills()

    assert result == {}


def test_find_global_untracked_skills_returns_sorted(isolated_home_for_skills):
    skills_dir = isolated_home_for_skills / ".claude" / "skills"
    for name in ["zebra-skill", "alpha-skill", "mango-skill"]:
        d = skills_dir / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Skill\n")

    result = _find_global_untracked_skills()

    assert result["claudecode"] == ["alpha-skill", "mango-skill", "zebra-skill"]


# ---------------------------------------------------------------------------
# Integration: abc delta output
# ---------------------------------------------------------------------------


@pytest.fixture
def project_base(temp_dir, valid_warehouse):
    """Minimal connected project with no tracked artifacts."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )
    return project


def test_delta_shows_project_scoped_agents_section(
    project_base, valid_warehouse, monkeypatch, isolated_home
):
    """Project-scoped Agents section appears when .claude/agents/ has files."""
    agents_dir = project_base / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "pipeline-developer.md").write_text("# Agent\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Project-scoped Agents" in result.output
    assert "pipeline-developer.md" in result.output
    assert "claudecode" in result.output


def test_delta_shows_project_scoped_agents_both_tools(
    project_base, valid_warehouse, monkeypatch, isolated_home
):
    """Both tools appear as columns when agents exist in both project dirs."""
    for tool_dir in [".claude", ".opencode"]:
        agents_dir = project_base / tool_dir / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "registra-ops.md").write_text("# Agent\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Project-scoped Agents" in result.output
    assert "registra-ops.md" in result.output
    assert "claudecode" in result.output
    assert "opencode" in result.output


def test_delta_no_project_scoped_agents_section_when_none_exist(
    project_base, monkeypatch, isolated_home
):
    """Project-scoped Agents section is absent when no project agent dirs have files."""
    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Project-scoped Agents" not in result.output


def test_delta_project_scoped_agents_summary_and_tip(
    project_base, monkeypatch, isolated_home
):
    """Summary line and promotion tip appear when project-scoped agents are found."""
    agents_dir = project_base / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "my-agent.md").write_text("# Agent\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Project-scoped agent(s)" in result.output
    assert "abc contribute" in result.output
    assert "coding agent" in result.output


def test_delta_shows_global_skills_section(project_base, monkeypatch, isolated_home):
    """Global Skills section appears when non-bundled skills exist in global dirs."""
    skill_dir = isolated_home / ".claude" / "skills" / "my-custom-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Custom skill\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Global Skills" in result.output
    assert "my-custom-skill" in result.output
    assert "claudecode" in result.output


def test_delta_shows_global_skills_both_tools(project_base, monkeypatch, isolated_home):
    """Both tool columns appear when the same skill is in both global dirs."""
    for skills_dir in [
        isolated_home / ".claude" / "skills",
        isolated_home / ".config" / "opencode" / "skills",
    ]:
        d = skills_dir / "sql-tools"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# SQL\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Global Skills" in result.output
    assert "sql-tools" in result.output
    assert "claudecode" in result.output
    assert "opencode" in result.output


def test_delta_no_global_skills_section_when_none_exist(
    project_base, monkeypatch, isolated_home
):
    """Global Skills section is absent when global skill dirs are empty."""
    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Global Skills" not in result.output


def test_delta_global_skills_excludes_bundled(project_base, monkeypatch, isolated_home):
    """Bundled skills in the global dir must not appear in the Global Skills section."""
    bundled = _bundled_skill_names()
    if not bundled:
        pytest.skip("No bundled skills to test exclusion")

    bundled_name = next(iter(bundled))
    skill_dir = isolated_home / ".claude" / "skills" / bundled_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Bundled\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Global Skills" not in result.output


def test_delta_global_skills_summary_and_tip(project_base, monkeypatch, isolated_home):
    """Summary count and tip appear when global untracked skills are found."""
    skill_dir = isolated_home / ".claude" / "skills" / "rogue-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Rogue\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Global skill(s)" in result.output
    assert "abc contribute" in result.output
    assert "coding agent" in result.output


def test_delta_both_reminder_sections_shown_together(
    project_base, monkeypatch, isolated_home
):
    """Both Project-scoped Agents and Global Skills sections appear simultaneously."""
    # Project-scoped agent
    (project_base / ".claude" / "agents").mkdir(parents=True)
    (project_base / ".claude" / "agents" / "my-agent.md").write_text("# Agent\n")

    # Global untracked skill
    skill_dir = isolated_home / ".claude" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Project-scoped Agents" in result.output
    assert "Global Skills" in result.output


def test_delta_no_differences_still_shows_reminder_sections(
    project_base, monkeypatch, isolated_home
):
    """Reminder sections appear even when all tracked artifacts are identical."""
    # No tracked artifacts → would normally say "No differences"
    # But project-scoped agents should still cause output
    (project_base / ".claude" / "agents").mkdir(parents=True)
    (project_base / ".claude" / "agents" / "hidden-agent.md").write_text("# Agent\n")

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "No differences found" not in result.output
    assert "Project-scoped Agents" in result.output


# ---------------------------------------------------------------------------
# GlobalSettings ignore patterns — _find_global_untracked_skills
# ---------------------------------------------------------------------------


def test_find_global_untracked_skills_respects_exact_ignore(isolated_home_for_skills):
    """A skill name listed exactly in ignore_patterns is excluded."""
    skill_dir = (
        isolated_home_for_skills / ".claude" / "skills" / "openspec-apply-change"
    )
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n")

    result = _find_global_untracked_skills(ignore_patterns=["openspec-apply-change"])

    assert result == {}


def test_find_global_untracked_skills_respects_glob_ignore(isolated_home_for_skills):
    """Glob patterns in ignore_patterns filter matching skills."""
    for name in ["openspec-apply-change", "openspec-propose", "my-custom-skill"]:
        d = isolated_home_for_skills / ".claude" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Skill\n")

    result = _find_global_untracked_skills(ignore_patterns=["openspec-*"])

    assert "claudecode" in result
    assert result["claudecode"] == ["my-custom-skill"]


def test_find_global_untracked_skills_no_ignore_patterns(isolated_home_for_skills):
    """Without ignore_patterns, all non-bundled skills are returned."""
    for name in ["openspec-apply-change", "my-skill"]:
        d = isolated_home_for_skills / ".claude" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Skill\n")

    result = _find_global_untracked_skills()

    assert result["claudecode"] == ["my-skill", "openspec-apply-change"]


def test_find_global_untracked_skills_multiple_patterns(isolated_home_for_skills):
    """Multiple ignore patterns all apply."""
    for name in ["openspec-apply-change", "opsx-enhance", "keep-this"]:
        d = isolated_home_for_skills / ".claude" / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Skill\n")

    result = _find_global_untracked_skills(ignore_patterns=["openspec-*", "opsx-*"])

    assert result["claudecode"] == ["keep-this"]


# ---------------------------------------------------------------------------
# GlobalSettings ignore patterns — _find_untracked_local_files
# ---------------------------------------------------------------------------


def test_find_untracked_local_files_skill_ignore_exact(tmp_path):
    """Exact skill name in ignore_patterns suppresses that skill."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    skills_root = tmp_path / "skills"
    skill_dir = skills_root / "openspec-apply-change"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n")

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        skills_paths={"claudecode": skills_root},
    )
    beacon_settings = BeaconManifest(
        artifacts={"knowledge": [], "skills": [], "contexts": []}
    )

    result = _find_untracked_local_files(
        comparator,
        beacon_settings,
        artifacts,
        ignore_patterns=["openspec-apply-change"],
    )

    assert result == []


def test_find_untracked_local_files_skill_ignore_glob(tmp_path):
    """Glob pattern in ignore_patterns filters matching skills, keeps others."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    skills_root = tmp_path / "skills"
    for name in ["openspec-apply-change", "openspec-propose", "my-skill"]:
        d = skills_root / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Skill\n")

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        skills_paths={"claudecode": skills_root},
    )
    beacon_settings = BeaconManifest(
        artifacts={"knowledge": [], "skills": [], "contexts": []}
    )

    result = _find_untracked_local_files(
        comparator, beacon_settings, artifacts, ignore_patterns=["openspec-*"]
    )

    paths = [rel for rel, _ in result]
    assert all("openspec" not in p for p in paths)
    assert any("my-skill" in p for p in paths)


def test_find_untracked_local_files_no_ignore_returns_all(tmp_path):
    """Without ignore_patterns, all untracked skills are returned."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    skills_root = tmp_path / "skills"
    for name in ["openspec-apply-change", "my-skill"]:
        d = skills_root / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# Skill\n")

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        skills_paths={"claudecode": skills_root},
    )
    beacon_settings = BeaconManifest(
        artifacts={"knowledge": [], "skills": [], "contexts": []}
    )

    result = _find_untracked_local_files(comparator, beacon_settings, artifacts)

    paths = [rel for rel, _ in result]
    assert any("openspec-apply-change" in p for p in paths)
    assert any("my-skill" in p for p in paths)


# ---------------------------------------------------------------------------
# BeaconSettings ignore field
# ---------------------------------------------------------------------------


def test_beacon_settings_ignore_defaults_empty(tmp_path):
    """BeaconSettings without ignore section defaults to empty ignore.skills."""
    yaml_path = tmp_path / "beacon.yaml"
    yaml_path.write_text("artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n")

    settings = BeaconManifest.from_yaml(yaml_path)

    assert settings.ignore.skills == []


def test_beacon_settings_ignore_skills_parsed(tmp_path):
    """beacon.yaml with ignore.skills is parsed into BeaconSettings.ignore.skills."""
    yaml_path = tmp_path / "beacon.yaml"
    yaml_path.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
        'ignore:\n  skills:\n    - "openspec-*"\n    - "opsx-*"\n'
    )

    settings = BeaconManifest.from_yaml(yaml_path)

    assert settings.ignore.skills == ["openspec-*", "opsx-*"]


def test_beacon_settings_ignore_empty_section(tmp_path):
    """An ignore section with no skills key defaults to empty list."""
    yaml_path = tmp_path / "beacon.yaml"
    yaml_path.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\nignore: {}\n"
    )

    settings = BeaconManifest.from_yaml(yaml_path)

    assert settings.ignore.skills == []


# ---------------------------------------------------------------------------
# Integration: abc delta respects beacon.yaml ignore patterns
# ---------------------------------------------------------------------------


def test_delta_ignores_global_skill_matching_pattern(
    project_base, monkeypatch, isolated_home
):
    """Global Skills section omits skills matching the beacon.yaml ignore pattern."""
    # Create openspec-style skill in global dir
    skill_dir = isolated_home / ".claude" / "skills" / "openspec-apply-change"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n")
    # Also create a skill that should still appear
    keep_dir = isolated_home / ".claude" / "skills" / "my-custom-skill"
    keep_dir.mkdir(parents=True)
    (keep_dir / "SKILL.md").write_text("# Custom\n")
    # Write ignore pattern into beacon.yaml
    (project_base / ".agentic-beacon" / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
        'ignore:\n  skills:\n    - "openspec-*"\n'
    )

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "openspec-apply-change" not in result.output
    assert "my-custom-skill" in result.output


def test_delta_hides_global_skills_section_when_all_ignored(
    project_base, monkeypatch, isolated_home
):
    """Global Skills section disappears entirely when all skills are ignored."""
    skill_dir = isolated_home / ".claude" / "skills" / "openspec-propose"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill\n")
    # Write ignore pattern into beacon.yaml
    (project_base / ".agentic-beacon" / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
        'ignore:\n  skills:\n    - "openspec-*"\n'
    )

    runner = CliRunner()
    monkeypatch.chdir(project_base)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Global Skills" not in result.output
