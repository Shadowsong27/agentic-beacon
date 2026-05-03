"""End-to-end integration tests for symlink-based artifact sync.

Covers tasks 7.8 (e2e sync+edit+contribute) and 8.3 (cross-project single source of truth).
"""

import os
import subprocess

import pytest
from beacon.cli.main import main
from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _git_env():
    """Return git environment with test author info."""
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


@pytest.fixture
def e2e_warehouse(tmp_path):
    """A warehouse initialised via 'abc warehouse init', then populated."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            "my-warehouse",
            "--path",
            str(tmp_path),
            "--org",
            "Test Org",
            "--languages",
            "python",
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, f"warehouse init failed:\n{result.output}"

    wh = tmp_path / "my-warehouse"

    # Add real artifacts
    (wh / "contexts" / "team.md").write_text("# Team Context\n")
    (wh / "knowledge" / "python").mkdir(parents=True, exist_ok=True)
    (wh / "knowledge" / "python" / "standards.md").write_text("# Python Standards\n")
    skill_dir = wh / "skills" / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Skill: Code Review\n")

    # Init git and commit
    env = _git_env()
    subprocess.run(["git", "init"], cwd=wh, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "."], cwd=wh, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )

    return wh


class TestSymlinkE2E:
    """Task 7.8: End-to-end integration test for sync+edit+contribute cycle."""

    def test_full_sync_edit_contribute_cycle(
        self, e2e_warehouse, tmp_path, monkeypatch
    ):
        """
        1. abc warehouse connect
        2. abc setup
        3. Edit beacon.yaml
        4. abc sync
        5. Assert symlink tree
        6. Edit a symlinked skill
        7. abc warehouse status
        8. abc warehouse contribute
        9. Assert commit in warehouse
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        runner = CliRunner()

        # Step 1: Connect
        result = runner.invoke(
            main, ["warehouse", "connect", "--path", str(e2e_warehouse)]
        )
        assert result.exit_code == 0, f"connect failed:\n{result.output}"

        # Step 2: Setup
        result = runner.invoke(main, ["setup", "--manual"])
        assert result.exit_code == 0, f"setup failed:\n{result.output}"

        # Step 3: Edit beacon.yaml
        beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n"
            "  knowledge:\n"
            "    - knowledge/python/standards.md\n"
            "  skills:\n"
            "    - skills/code-review/\n"
            "  contexts:\n"
            "    - contexts/team.md\n"
        )

        # Step 4: Sync
        result = runner.invoke(main, ["sync"])
        assert result.exit_code == 0, f"sync failed:\n{result.output}"

        # Step 5: Assert symlink tree
        artifacts = project_dir / ".agentic-beacon" / "artifacts"
        symlinks = list(artifacts.rglob("*"))
        symlink_count = sum(1 for p in symlinks if p.is_symlink())
        regular_count = sum(1 for p in symlinks if p.is_file() and not p.is_symlink())
        assert symlink_count > 0, "No symlinks found in artifacts tree"
        assert regular_count == 0, (
            f"Found {regular_count} regular files in artifacts tree"
        )

        # Verify specific symlinks exist
        assert (artifacts / "knowledge" / "python" / "standards.md").is_symlink()
        assert (artifacts / "skills" / "code-review" / "SKILL.md").is_symlink()
        assert (artifacts / "contexts" / "team.md").is_symlink()

        # Step 6: Edit a symlinked skill
        skill_path = artifacts / "skills" / "code-review" / "SKILL.md"
        skill_path.write_text("# Skill: Code Review\n## Local edit\n")

        # Step 7: Warehouse status
        result = runner.invoke(main, ["warehouse", "status"])
        assert result.exit_code == 0, f"status failed:\n{result.output}"
        # Output should mention the edited file
        assert "code-review" in result.output or "SKILL.md" in result.output

        # Step 8: Contribute
        result = runner.invoke(main, ["warehouse", "contribute", "-m", "test edit"])
        assert result.exit_code == 0, f"contribute failed:\n{result.output}"

        # Step 9: Assert commit in warehouse
        env = _git_env()
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=e2e_warehouse,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "test edit" in log.stdout

        # Verify diff contains the appended text
        diff = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            cwd=e2e_warehouse,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Local edit" in diff.stdout


class TestCrossProjectSingleSourceOfTruth:
    """Task 8.3: Cross-project single-source-of-truth regression test."""

    def test_cross_project_single_source_of_truth(
        self, e2e_warehouse, tmp_path, monkeypatch
    ):
        """
        Two projects both connected to the same warehouse, both synced.
        Edit a skill from project A.
        Assert reading the skill via project B's symlink path returns A's edit
        IMMEDIATELY (no sync step).
        abc warehouse contribute from B commits cleanly.
        """
        project_a = tmp_path / "project-a"
        project_b = tmp_path / "project-b"
        project_a.mkdir()
        project_b.mkdir()

        for project_dir in [project_a, project_b]:
            monkeypatch.chdir(project_dir)
            runner = CliRunner()

            # Connect and setup
            result = runner.invoke(
                main, ["warehouse", "connect", "--path", str(e2e_warehouse)]
            )
            assert result.exit_code == 0

            result = runner.invoke(main, ["setup", "--manual"])
            assert result.exit_code == 0

            beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
            beacon_yaml.write_text(
                "artifacts:\n"
                "  skills:\n"
                "    - skills/code-review/\n"
                "  knowledge: []\n"
                "  contexts: []\n"
            )

            result = runner.invoke(main, ["sync"])
            assert result.exit_code == 0

        # Edit skill from project A
        skill_a = (
            project_a
            / ".agentic-beacon"
            / "artifacts"
            / "skills"
            / "code-review"
            / "SKILL.md"
        )
        skill_a.write_text("# Skill: Code Review\n## Edit from project A\n")

        # Reading via project B should show the edit IMMEDIATELY
        skill_b = (
            project_b
            / ".agentic-beacon"
            / "artifacts"
            / "skills"
            / "code-review"
            / "SKILL.md"
        )
        content_b = skill_b.read_text()
        assert "Edit from project A" in content_b, (
            "Project B should see project A's edit immediately via symlink"
        )

        # Contribute from B should commit cleanly
        monkeypatch.chdir(project_b)
        runner = CliRunner()
        result = runner.invoke(
            main, ["warehouse", "contribute", "-m", "Cross-project edit"]
        )
        assert result.exit_code == 0, f"contribute from B failed:\n{result.output}"

        # Verify commit in warehouse
        env = _git_env()
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=e2e_warehouse,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Cross-project edit" in log.stdout
