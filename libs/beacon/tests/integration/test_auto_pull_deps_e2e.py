"""End-to-end tests for auto-pull-artifact-dependencies (Phase 10).

Covers tasks 10.1–10.4:
- 10.1: Init → adopt → sync with derived knowledge symlinks
- 10.2: Unadopt context → sync prunes knowledge symlinks
- 10.3: Legacy beacon.yaml with knowledge list → migration
- 10.4: Adopted agent with unadopted dependency → error with migration URL
"""

import os
import subprocess
from pathlib import Path

import pytest
import yaml
from beacon.cli.main import main
from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _git_env():
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


def _git_init(path: Path) -> None:
    env = _git_env()
    subprocess.run(["git", "init"], cwd=path, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )


def _git_add_commit(path: Path, message: str = "add files") -> str:
    env = _git_env()
    subprocess.run(
        ["git", "add", "-A"], cwd=path, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, env=env
    )
    return result.stdout.strip()


@pytest.fixture
def warehouse_with_knowledge_refs(tmp_path):
    """Warehouse with contexts that reference knowledge files."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "docs").mkdir()
    (wh / "README.md").write_text("# Test Warehouse\n")

    # Create knowledge files
    (wh / "knowledge" / "python").mkdir(parents=True)
    (wh / "knowledge" / "python" / "standards.md").write_text("# Python Standards\n")
    (wh / "knowledge" / "testing").mkdir(parents=True)
    (wh / "knowledge" / "testing" / "tdd.md").write_text("# TDD\n")

    # Create a context that references two knowledge files
    (wh / "contexts" / "team.md").write_text(
        "# Team Context\n"
        "See [Python Standards](../knowledge/python/standards.md)\n"
        "And [TDD](../knowledge/testing/tdd.md)\n"
    )

    # Create another context with no knowledge links
    (wh / "contexts" / "plain.md").write_text("# Plain Context\nNo links here.\n")

    # Create a skill with no knowledge links
    skill_dir = wh / "skills" / "code-review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: []\n---\n# Skill: Code Review\n"
    )

    # Create agent files (no requires: frontmatter — dependencies live in agents.yaml)
    (wh / "agents" / "reviewer.md").write_text(
        "---\nname: reviewer\n---\n# Reviewer Agent\n"
    )

    (wh / "agents" / "broken.md").write_text("---\nname: broken\n---\n# Broken Agent\n")

    # Create agents.yaml matching the agent files
    (wh / "agents" / "agents.yaml").write_text(
        yaml.safe_dump({"reviewer": {"skills": []}, "broken": {"skills": []}})
    )

    _git_init(wh)
    _git_add_commit(wh, "init")

    return wh


@pytest.fixture
def project_dir(tmp_path, warehouse_with_knowledge_refs, monkeypatch):
    """A project directory connected to the warehouse."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(warehouse_with_knowledge_refs)]
    )
    assert result.exit_code == 0, f"connect failed: {result.output}"

    result = runner.invoke(main, ["setup"])
    assert result.exit_code == 0, f"setup failed: {result.output}"

    return project


# ---------------------------------------------------------------------------
# 10.1: E2E — adopt context → sync → knowledge symlinks appear
# ---------------------------------------------------------------------------


def test_e2e_adopt_context_creates_knowledge_symlinks(project_dir, monkeypatch):
    """Adopting a context that references knowledge files creates knowledge symlinks."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/team.md\n  skills: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0, f"sync failed: {result.output}"

    artifacts = project_dir / ".agentic-beacon" / "artifacts"

    # The adopted context should be present
    assert (artifacts / "contexts" / "team.md").exists()

    # The two referenced knowledge files should be present as symlinks
    assert (artifacts / "knowledge" / "python" / "standards.md").exists()
    assert (artifacts / "knowledge" / "testing" / "tdd.md").exists()

    # The unadopted context should NOT create knowledge symlinks
    assert not (artifacts / "contexts" / "plain.md").exists()

    # Count knowledge symlinks — should be exactly 2
    knowledge_dir = artifacts / "knowledge"
    if knowledge_dir.exists():
        knowledge_symlinks = list(knowledge_dir.rglob("*.md"))
        assert len(knowledge_symlinks) == 2, (
            f"Expected 2 knowledge symlinks, got {len(knowledge_symlinks)}: {knowledge_symlinks}"
        )


# ---------------------------------------------------------------------------
# 10.2: E2E — unadopt context → sync prunes knowledge symlinks
# ---------------------------------------------------------------------------


def test_e2e_unadopt_context_prunes_knowledge_symlinks(
    project_dir, warehouse_with_knowledge_refs, monkeypatch
):
    """Removing a context prunes its orphaned knowledge symlinks."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Add another context that references a different knowledge file
    wh = warehouse_with_knowledge_refs
    (wh / "contexts" / "qa.md").write_text(
        "# QA Context\nSee [TDD](../knowledge/testing/tdd.md)\n"
    )
    _git_add_commit(wh, "add qa context")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/team.md\n"
        "    - contexts/qa.md\n"
        ""
        "  skills: []\n"
    )

    # First sync
    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0

    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "knowledge" / "python" / "standards.md").exists()
    assert (artifacts / "knowledge" / "testing" / "tdd.md").exists()

    # Now unadopt team.md (but keep qa.md)
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/qa.md\n  skills: []\n"
    )

    # Sync again — should prune orphaned knowledge symlinks
    result = runner.invoke(main, ["sync", "--skip-git-check"], input="y\n")
    assert result.exit_code == 0, f"second sync failed: {result.output}"

    # qa.md's knowledge symlink should remain
    assert (artifacts / "knowledge" / "testing" / "tdd.md").exists()

    # team.md's orphaned knowledge symlink should be removed
    assert not (artifacts / "knowledge" / "python" / "standards.md").exists()


# ---------------------------------------------------------------------------
# 10.3: E2E — legacy beacon.yaml with knowledge list → migration
# ---------------------------------------------------------------------------


def test_e2e_legacy_beacon_yaml_migration(
    project_dir, warehouse_with_knowledge_refs, monkeypatch
):
    """Legacy beacon.yaml with knowledge list is silently migrated on sync.

    The legacy knowledge key is dropped from the in-memory loader and the file
    is rewritten on disk. Subsequent loads do not emit migration logs.
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    # Write a legacy beacon.yaml with knowledge key
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  contexts:\n"
        "    - contexts/team.md\n"
        "  skills: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0, f"sync failed: {result.output}"

    # Assert: exactly one INFO record about migration in output
    migration_logs = [
        line
        for line in result.output.splitlines()
        if "artifacts.knowledge removed" in line
    ]
    assert len(migration_logs) == 1, (
        f"Expected 1 migration log, got {len(migration_logs)}. Output:\n{result.output}"
    )

    # Assert: knowledge symlinks reflect derived set (from context links)
    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "knowledge" / "python" / "standards.md").exists()
    assert (artifacts / "knowledge" / "testing" / "tdd.md").exists()

    # Assert: file on disk was rewritten without knowledge key
    content = beacon_yaml.read_text()
    assert "knowledge:" not in content
    assert "contexts:" in content
    assert "skills:" in content

    # Sync again — no migration log this time because file is clean
    result2 = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result2.exit_code == 0, f"second sync failed: {result2.output}"
    migration_logs2 = [
        line
        for line in result2.output.splitlines()
        if "artifacts.knowledge removed" in line
    ]
    assert len(migration_logs2) == 0, (
        f"Expected 0 migration logs on second sync, got {len(migration_logs2)}"
    )


# ---------------------------------------------------------------------------
# 10.4: E2E — sync does not install agents globally (PER-109 deferred)
# ---------------------------------------------------------------------------


def test_e2e_sync_does_not_install_agents(project_dir, monkeypatch, isolated_home):
    """Sync must not call sync_agents_from_warehouse or install agents globally."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/team.md\n  skills: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0, f"sync failed: {result.output}"

    # No agent should appear in global dirs
    for d in [
        isolated_home / ".config" / "opencode" / "agents",
        isolated_home / ".claude" / "agents",
    ]:
        if d.exists():
            assert not any(
                f.suffix == ".md" and f.name != "README.md" for f in d.rglob("*")
            ), f"Unexpected agent files in {d}"


# ---------------------------------------------------------------------------
# 10.4b: E2E — skill-required context auto-pulled transitively
# ---------------------------------------------------------------------------


def test_e2e_skill_context_auto_pulled(
    project_dir, warehouse_with_knowledge_refs, monkeypatch
):
    """Skill requiring a context that is not in beacon.yaml is auto-pulled."""
    wh = warehouse_with_knowledge_refs
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Add a skill that requires a context
    skill_dir = wh / "skills" / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: [team]\n---\n# Skill\n"
    )
    _git_add_commit(wh, "add skill with dep")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts: []\n  skills:\n    - skills/code-review/\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0, f"sync failed: {result.output}"

    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    # The transitive context should have been synced
    assert (artifacts / "contexts" / "team.md").exists()
    assert (artifacts / "skills" / "code-review" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# 10.4c: E2E — missing skill-required context fails with migration URL
# ---------------------------------------------------------------------------


def test_e2e_missing_skill_context_shows_migration_url(
    project_dir, warehouse_with_knowledge_refs, monkeypatch
):
    """Skill requiring a non-existent context fails sync with migration URL."""
    wh = warehouse_with_knowledge_refs
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Add a skill that requires a missing context
    skill_dir = wh / "skills" / "broken-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: [missing-context]\n---\n# Broken\n"
    )
    _git_add_commit(wh, "add broken skill")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts: []\n  skills:\n    - skills/broken-skill/\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code != 0, (
        f"Expected non-zero exit, got 0. Output: {result.output}"
    )

    output = result.output
    assert "missing-context" in output.lower(), (
        f"Expected missing context name in output: {output}"
    )
    assert "docs/migrations/artifact-dependencies-frontmatter.md" in output, (
        f"Expected migration doc URL in output: {output}"
    )


# ---------------------------------------------------------------------------
# Regression: full unadoption prunes all knowledge symlinks
# ---------------------------------------------------------------------------


def test_e2e_full_unadoption_prunes_all_knowledge_symlinks(project_dir, monkeypatch):
    """Removing all artifacts prunes all orphaned knowledge symlinks and empty dirs."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/team.md\n  skills: []\n"
    )

    # First sync
    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0, f"first sync failed: {result.output}"

    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "contexts" / "team.md").exists()
    assert (artifacts / "knowledge" / "python" / "standards.md").exists()
    assert (artifacts / "knowledge" / "testing" / "tdd.md").exists()

    # Now unadopt everything
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")

    # Sync again — should prune all orphaned symlinks
    result = runner.invoke(main, ["sync", "--skip-git-check"], input="y\n")
    assert result.exit_code == 0, f"second sync failed: {result.output}"

    # All knowledge symlinks should be removed
    assert not (artifacts / "knowledge").exists(), (
        "knowledge dir should not exist after full unadoption"
    )

    # Context symlink should also be removed
    assert not (artifacts / "contexts" / "team.md").exists()
