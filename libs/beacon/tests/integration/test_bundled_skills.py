"""Tests for bundled skill auto-installation (PER-43).

Bundled skills are installed into global agent skill directories
(~/.config/opencode/skills/, ~/.claude/skills/) rather than per-project dirs.
All tests redirect the global dirs to tmp_path via bundled_global_skill_dirs patch.

Covers:
  - Unit tests for install_bundled_skills_globally
  - Unit tests for show_bundled_skills_status
  - Integration tests: abc sync auto-installs bundled skills globally
  - Integration tests: early-exit path (empty beacon.yaml) still installs
  - Integration tests: updates propagate when abc is upgraded
  - Integration tests: abc status shows bundled skills table
"""

import io
import json
from pathlib import Path
from unittest.mock import patch

from beacon.cli.main import main
from beacon.domains.artifact.skill import (
    install_bundled_skills_globally,
    show_bundled_skills_status,
)
from click.testing import CliRunner
from rich.console import Console

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BUNDLED_SKILL_NAME = "record-knowledge"


def _real_bundled_skill_content() -> str:
    """Return the actual SKILL.md content from data/skills/."""
    import beacon.cli as cli_module

    skill_file = (
        Path(cli_module.__file__).parent.parent
        / "data"
        / "skills"
        / BUNDLED_SKILL_NAME
        / "SKILL.md"
    )
    return skill_file.read_text(encoding="utf-8")


def _fake_global_dirs(tmp_path: Path) -> dict[str, Path]:
    """Return fake global skill dirs rooted in tmp_path (safe for tests)."""
    return {
        "opencode": tmp_path / "global" / "opencode" / "skills",
        "claudecode": tmp_path / "global" / "claude" / "skills",
    }


def _capture_bundled_skills_status(global_dirs: dict[str, Path]) -> str:
    """Run show_bundled_skills_status with patched global dirs and return rendered output."""
    buf = io.StringIO()
    real_console = Console(file=buf, highlight=False, markup=False)
    with (
        patch("beacon.domains.artifact.skill.console", real_console),
        patch(
            "beacon.domains.artifact.skill.bundled_global_skill_dirs",
            return_value=global_dirs,
        ),
    ):
        show_bundled_skills_status()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Unit tests: install_bundled_skills_globally
# ---------------------------------------------------------------------------


def test_install_bundled_skills_globally_opencode(tmp_path):
    """Bundled skills are written to the global opencode skills dir."""
    fake_dirs = _fake_global_dirs(tmp_path)

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        installed, errors = install_bundled_skills_globally()

    assert errors == []
    assert any(
        BUNDLED_SKILL_NAME in entry and "opencode" in entry for entry in installed
    )
    skill_file = fake_dirs["opencode"] / BUNDLED_SKILL_NAME / "SKILL.md"
    assert skill_file.exists()
    assert skill_file.read_text(encoding="utf-8") == _real_bundled_skill_content()


def test_install_bundled_skills_globally_claudecode(tmp_path):
    """Bundled skills are written to the global claudecode skills dir."""
    fake_dirs = _fake_global_dirs(tmp_path)

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        installed, errors = install_bundled_skills_globally()

    assert errors == []
    assert any(
        BUNDLED_SKILL_NAME in entry and "claudecode" in entry for entry in installed
    )
    skill_file = fake_dirs["claudecode"] / BUNDLED_SKILL_NAME / "SKILL.md"
    assert skill_file.exists()
    assert skill_file.read_text(encoding="utf-8") == _real_bundled_skill_content()


def test_install_bundled_skills_globally_both_dirs(tmp_path):
    """Both global dirs are populated in a single call."""
    fake_dirs = _fake_global_dirs(tmp_path)

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        installed, errors = install_bundled_skills_globally()

    assert errors == []
    assert (fake_dirs["opencode"] / BUNDLED_SKILL_NAME / "SKILL.md").exists()
    assert (fake_dirs["claudecode"] / BUNDLED_SKILL_NAME / "SKILL.md").exists()


def test_install_bundled_skills_globally_idempotent(tmp_path):
    """Second call returns empty installed list when content is unchanged."""
    fake_dirs = _fake_global_dirs(tmp_path)

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        install_bundled_skills_globally()
        installed_second, errors = install_bundled_skills_globally()

    assert errors == []
    assert installed_second == []


def test_install_bundled_skills_globally_updates_on_content_change(tmp_path):
    """When the bundled skill content differs (e.g. abc upgrade), the file is overwritten."""
    fake_dirs = _fake_global_dirs(tmp_path)
    stale_content = "# Stale version from old abc release\n"

    for skills_root in fake_dirs.values():
        dest = skills_root / BUNDLED_SKILL_NAME
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text(stale_content)

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        installed, errors = install_bundled_skills_globally()

    assert errors == []
    assert any(BUNDLED_SKILL_NAME in entry for entry in installed)
    for skills_root in fake_dirs.values():
        content = (skills_root / BUNDLED_SKILL_NAME / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert content != stale_content
        assert content == _real_bundled_skill_content()


def test_install_bundled_skills_globally_no_agent_detection_required(tmp_path):
    """Global install does not require any agent config in the project."""
    fake_dirs = _fake_global_dirs(tmp_path)
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # Deliberately no opencode.json, no .claude/

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        installed, errors = install_bundled_skills_globally()

    assert errors == []
    assert any(BUNDLED_SKILL_NAME in entry for entry in installed)


# ---------------------------------------------------------------------------
# Unit tests: show_bundled_skills_status
# ---------------------------------------------------------------------------


def test_show_bundled_skills_status_installed(tmp_path):
    """Shows ✓ for a bundled skill installed in both global dirs."""
    fake_dirs = _fake_global_dirs(tmp_path)
    for skills_root in fake_dirs.values():
        dest = skills_root / BUNDLED_SKILL_NAME
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text("# Skill")

    output = _capture_bundled_skills_status(fake_dirs)

    assert BUNDLED_SKILL_NAME in output
    assert "✓" in output


def test_show_bundled_skills_status_not_installed(tmp_path):
    """Shows ✗ for a bundled skill that has not been installed."""
    fake_dirs = _fake_global_dirs(tmp_path)

    output = _capture_bundled_skills_status(fake_dirs)

    assert BUNDLED_SKILL_NAME in output
    assert "✗" in output


def test_show_bundled_skills_status_partial(tmp_path):
    """Shows ✗ if the skill is only installed in one of the two global dirs."""
    fake_dirs = _fake_global_dirs(tmp_path)
    dest = fake_dirs["opencode"] / BUNDLED_SKILL_NAME
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text("# Skill")

    output = _capture_bundled_skills_status(fake_dirs)

    assert BUNDLED_SKILL_NAME in output
    assert "✗" in output


def test_show_bundled_skills_status_shows_global_label(tmp_path):
    """Status table title indicates global scope."""
    fake_dirs = _fake_global_dirs(tmp_path)

    output = _capture_bundled_skills_status(fake_dirs)

    assert "global" in output.lower()


# ---------------------------------------------------------------------------
# Integration tests: abc sync auto-installs bundled skills globally
# ---------------------------------------------------------------------------


def test_sync_installs_bundled_skills_globally(valid_warehouse, temp_dir, monkeypatch):
    """abc sync installs bundled skills into global dirs (not per-project)."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    assert (fake_dirs["opencode"] / BUNDLED_SKILL_NAME / "SKILL.md").exists()
    assert (fake_dirs["claudecode"] / BUNDLED_SKILL_NAME / "SKILL.md").exists()


def test_sync_installs_bundled_skills_to_project_dir(
    valid_warehouse, temp_dir, monkeypatch
):
    """abc sync writes bundled skills to per-project .opencode/skills/ with command stubs."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    (project_dir / "opencode.json").write_text(json.dumps({}))

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        runner.invoke(main, ["sync", "--skip-git-check"])

    assert (
        project_dir / ".opencode" / "skills" / BUNDLED_SKILL_NAME / "SKILL.md"
    ).exists()
    assert (project_dir / ".opencode" / "command" / f"{BUNDLED_SKILL_NAME}.md").exists()


def test_sync_reports_bundled_skill_installation(
    valid_warehouse, temp_dir, monkeypatch
):
    """abc sync output mentions the installed bundled skill name."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    assert BUNDLED_SKILL_NAME in result.output
    assert (
        "managed by abc" in result.output.lower() or "bundled" in result.output.lower()
    )


def test_sync_bundled_skills_idempotent(valid_warehouse, temp_dir, monkeypatch):
    """Second abc sync does not report bundled skills as installed when unchanged."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        runner.invoke(main, ["sync", "--skip-git-check"])
        result_second = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result_second.exit_code == 0
    assert "installed bundled" not in result_second.output.lower()


# ---------------------------------------------------------------------------
# Integration tests: early-exit path (empty beacon.yaml) still installs
# ---------------------------------------------------------------------------


def test_sync_empty_beacon_yaml_still_installs_bundled_skills(
    valid_warehouse, temp_dir, monkeypatch
):
    """abc sync with no configured artifacts still auto-installs bundled skills globally."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    assert "no artifacts" in result.output.lower()
    assert (fake_dirs["opencode"] / BUNDLED_SKILL_NAME / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Integration tests: updates propagate when abc is upgraded
# ---------------------------------------------------------------------------


def test_sync_overwrites_stale_bundled_skill(valid_warehouse, temp_dir, monkeypatch):
    """abc sync updates a bundled skill that differs from the shipped version."""
    fake_dirs = _fake_global_dirs(temp_dir)
    stale_content = "# Stale version from old abc release\n"

    for skills_root in fake_dirs.values():
        dest = skills_root / BUNDLED_SKILL_NAME
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text(stale_content)

    runner = CliRunner()
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    for skills_root in fake_dirs.values():
        content = (skills_root / BUNDLED_SKILL_NAME / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert content != stale_content
        assert content == _real_bundled_skill_content()
    assert BUNDLED_SKILL_NAME in result.output


# ---------------------------------------------------------------------------
# Integration tests: abc status shows bundled skills table
# ---------------------------------------------------------------------------


def test_status_shows_bundled_skills_table(valid_warehouse, temp_dir, monkeypatch):
    """abc status displays a bundled skills table with global label."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        runner.invoke(main, ["sync", "--skip-git-check"])
        result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert BUNDLED_SKILL_NAME in result.output
    assert "global" in result.output.lower()


def test_status_shows_check_for_installed_bundled_skill(
    valid_warehouse, temp_dir, monkeypatch
):
    """abc status shows ✓ for a bundled skill installed in both global dirs."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        runner.invoke(main, ["sync", "--skip-git-check"])
        result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert f"✓ {BUNDLED_SKILL_NAME}" in result.output


def test_status_shows_cross_for_uninstalled_bundled_skill(
    valid_warehouse, temp_dir, monkeypatch
):
    """abc status shows ✗ for a bundled skill not yet installed globally."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    (project_dir / ".agentic-beacon" / "artifacts").mkdir(parents=True)

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert f"✗ {BUNDLED_SKILL_NAME}" in result.output


def test_status_bundled_skills_visible_before_sync(
    valid_warehouse, temp_dir, monkeypatch
):
    """abc status shows the bundled skills table even before any sync."""
    fake_dirs = _fake_global_dirs(temp_dir)
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    with patch(
        "beacon.domains.artifact.skill.bundled_global_skill_dirs",
        return_value=fake_dirs,
    ):
        result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert BUNDLED_SKILL_NAME in result.output
