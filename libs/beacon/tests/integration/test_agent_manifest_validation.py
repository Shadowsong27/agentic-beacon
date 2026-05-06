"""Integration tests for agent manifest validation in warehouse status and sync.

Covers tasks 2.1–2.5 from move-agent-requires-to-warehouse-manifest OpenSpec change.
"""

import os
import subprocess
from pathlib import Path

import yaml
from beacon.cli.main import main
from beacon.core.dependencies.manifest import MIGRATION_DOC_URL
from click.testing import CliRunner


def _init_git(path: Path) -> None:
    """Initialize a git repo at path with a dummy commit."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }
    subprocess.run(["git", "init"], cwd=path, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "."], cwd=path, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )


def _make_warehouse_with_agents(tmp_path: Path) -> Path:
    """Create a warehouse with an agent file and a skill, initialised as a git repo."""
    wh = tmp_path / "warehouse"
    for d in ("agents", "contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir(parents=True)
    (wh / "README.md").write_text("# Warehouse")

    # Create a skill
    (wh / "skills" / "my-skill").mkdir()
    (wh / "skills" / "my-skill" / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: []\n---\n# Skill\n"
    )

    # Create an agent file
    (wh / "agents" / "my-agent.md").write_text("---\nname: my-agent\n---\n# Agent\n")

    # Create agents.yaml
    data = {"my-agent": {"skills": ["my-skill"]}}
    (wh / "agents" / "agents.yaml").write_text(yaml.safe_dump(data))

    _init_git(wh)
    return wh


def _connect_project(project_dir: Path, warehouse_path: Path) -> None:
    """Connect a project to a warehouse."""
    beacon_dir = project_dir / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse_path}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  skills: []\n  contexts: []\n"
    )


# ---------------------------------------------------------------------------
# 2.1 / 2.2: abc warehouse status surfaces agent manifest errors
# ---------------------------------------------------------------------------


class TestWarehouseStatusAgentManifestValidation:
    def test_status_fails_when_agent_missing_from_manifest(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)
        # Remove the agent from agents.yaml so file exists but no manifest entry
        (wh / "agents" / "agents.yaml").write_text("{}")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["warehouse", "status"])

        assert result.exit_code == 1
        assert "my-agent.md has no entry" in result.output
        assert MIGRATION_DOC_URL in result.output

    def test_status_fails_when_requires_frontmatter_present(
        self, tmp_path, monkeypatch
    ):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)
        # Add requires: frontmatter to the agent file
        (wh / "agents" / "my-agent.md").write_text(
            "---\nname: my-agent\nrequires:\n  contexts: [c]\n---\n# Agent\n"
        )
        _init_git(wh)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["warehouse", "status"])

        assert result.exit_code == 1
        assert "requires:" in result.output
        assert MIGRATION_DOC_URL in result.output

    def test_status_fails_when_declared_skill_missing(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)
        # Remove the skill directory
        import shutil

        shutil.rmtree(wh / "skills" / "my-skill")
        _init_git(wh)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["warehouse", "status"])

        assert result.exit_code == 1
        assert "my-skill" in result.output
        assert "SKILL.md" in result.output
        assert MIGRATION_DOC_URL in result.output

    def test_status_passes_when_manifest_valid(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["warehouse", "status"])

        assert result.exit_code == 0
        # Should show clean working tree
        assert "clean" in result.output.lower() or "modified" in result.output.lower()

    def test_status_passes_when_agents_dir_empty(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = tmp_path / "warehouse"
        for d in ("agents", "contexts", "knowledge", "skills", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# Warehouse")
        _init_git(wh)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["warehouse", "status"])

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 2.3: abc sync fails fast on agent manifest errors
# ---------------------------------------------------------------------------


class TestSyncAgentManifestValidation:
    def test_sync_fails_when_agent_missing_from_manifest(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)
        (wh / "agents" / "agents.yaml").write_text("{}")
        _init_git(wh)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 1
        assert "my-agent.md has no entry" in result.output
        assert MIGRATION_DOC_URL in result.output

    def test_sync_fails_when_requires_frontmatter_present(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)
        (wh / "agents" / "my-agent.md").write_text(
            "---\nname: my-agent\nrequires:\n  contexts: [c]\n---\n# Agent\n"
        )
        _init_git(wh)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 1
        assert "requires:" in result.output
        assert MIGRATION_DOC_URL in result.output

    def test_sync_passes_when_manifest_valid(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0

    def test_sync_passes_when_agents_dir_empty(self, tmp_path, monkeypatch):
        runner = CliRunner()

        wh = tmp_path / "warehouse"
        for d in ("agents", "contexts", "knowledge", "skills", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# Warehouse")
        _init_git(wh)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# 2.4: abc install agents/<name>.md and sync_agents_from_warehouse unchanged
# ---------------------------------------------------------------------------


class TestAgentsSyncUnchanged:
    def test_agents_sync_still_works(self, tmp_path, monkeypatch):
        """abc agents sync should still work and not be affected by manifest validation."""
        runner = CliRunner()

        wh = _make_warehouse_with_agents(tmp_path)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        _connect_project(project_dir, wh)

        result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

        # agents sync should succeed regardless of manifest state
        # (it doesn't validate the manifest)
        assert result.exit_code == 0
