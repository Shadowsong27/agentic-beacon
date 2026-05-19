"""Direct unit tests for beacon.domains.warehouse._tracked_paths.get_tracked_paths.

PER-183 regression: the function must walk all three artifact types declared
by ArtifactsConfig (skills, contexts, agents). Before PER-183 was fixed, only
skills + contexts were walked, silently dropping agent contributions from the
contribute flow.

Knowledge files are intentionally NOT in scope — they are auto-derived during
abc sync / abc adopt from context+skill references and are not part of the
beacon.yaml-tracked manifest.
"""

from __future__ import annotations

from pathlib import Path

from beacon.domains.warehouse._tracked_paths import get_tracked_paths


def _write_beacon_yaml(
    warehouse: Path,
    *,
    skills: list[str] | None = None,
    contexts: list[str] | None = None,
    agents: list[str] | None = None,
) -> Path:
    """Write a minimal beacon.yaml with the requested artifact sections."""
    ab_dir = warehouse / ".agentic-beacon"
    ab_dir.mkdir(exist_ok=True)
    beacon_yaml = ab_dir / "beacon.yaml"

    def _section(name: str, items: list[str] | None) -> str:
        if items is None:
            return f"  {name}: []\n"
        if not items:
            return f"  {name}: []\n"
        lines = "\n".join(f"    - {p}" for p in items)
        return f"  {name}:\n{lines}\n"

    body = (
        "version: 1\nartifacts:\n"
        + _section("skills", skills)
        + _section("contexts", contexts)
        + _section("agents", agents)
    )
    beacon_yaml.write_text(body)
    return beacon_yaml


def _init_git(warehouse: Path) -> None:
    """Initialize a git repo in warehouse and configure user."""
    import subprocess

    subprocess.run(["git", "init", str(warehouse)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(warehouse), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(warehouse), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )


class TestGetTrackedPathsArtifactsCoverage:
    """PER-183: walking artifacts.skills + contexts + agents — all three."""

    def test_agents_listed_returns_agent_path(self, tmp_path):
        """Agent declared in artifacts.agents → returned by get_tracked_paths."""
        wh = tmp_path / "warehouse"
        (wh / "agents").mkdir(parents=True)
        (wh / "agents" / "alpha.md").write_text("---\nname: alpha\n---\n")
        beacon_yaml = _write_beacon_yaml(wh, agents=["agents/alpha.md"])

        result = get_tracked_paths(wh, beacon_yaml)
        assert "agents/alpha.md" in result, (
            f"PER-183 regression: agent should appear in tracked paths. Got: {result}"
        )

    def test_all_three_types_returned_together(self, tmp_path):
        """skills + contexts + agents all populated → all paths returned."""
        wh = tmp_path / "warehouse"
        (wh / "agents").mkdir(parents=True)
        (wh / "contexts").mkdir(parents=True)
        (wh / "skills" / "s1").mkdir(parents=True)
        (wh / "agents" / "a1.md").write_text("---\nname: a1\n---\n")
        (wh / "contexts" / "c1.md").write_text("# c1\n")
        (wh / "skills" / "s1" / "SKILL.md").write_text("---\nname: s1\n---\n")

        beacon_yaml = _write_beacon_yaml(
            wh,
            skills=["skills/s1/SKILL.md"],
            contexts=["contexts/c1.md"],
            agents=["agents/a1.md"],
        )

        result = sorted(get_tracked_paths(wh, beacon_yaml))
        assert result == sorted(
            ["skills/s1/SKILL.md", "contexts/c1.md", "agents/a1.md"]
        ), f"all three artifact types should appear, got: {result}"

    def test_empty_agents_section_returns_only_skills_and_contexts(self, tmp_path):
        """artifacts.agents: [] → only the other two types are returned."""
        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        (wh / "contexts" / "c1.md").write_text("# c1\n")
        beacon_yaml = _write_beacon_yaml(wh, contexts=["contexts/c1.md"], agents=[])

        result = get_tracked_paths(wh, beacon_yaml)
        assert result == ["contexts/c1.md"]

    def test_only_agents_section_returns_just_agents(self, tmp_path):
        """artifacts: agents only (skills + contexts empty) → only agents."""
        wh = tmp_path / "warehouse"
        (wh / "agents").mkdir(parents=True)
        (wh / "agents" / "solo.md").write_text("---\nname: solo\n---\n")
        beacon_yaml = _write_beacon_yaml(wh, agents=["agents/solo.md"])

        result = get_tracked_paths(wh, beacon_yaml)
        assert result == ["agents/solo.md"]

    def test_agents_directory_pattern_walks_recursively(self, tmp_path):
        """artifacts.agents: [agents/] picks up every file inside the directory."""
        wh = tmp_path / "warehouse"
        (wh / "agents").mkdir(parents=True)
        (wh / "agents" / "one.md").write_text("---\nname: one\n---\n")
        (wh / "agents" / "two.md").write_text("---\nname: two\n---\n")
        beacon_yaml = _write_beacon_yaml(wh, agents=["agents/"])

        result = sorted(get_tracked_paths(wh, beacon_yaml))
        assert "agents/one.md" in result
        assert "agents/two.md" in result

    def test_missing_beacon_yaml_returns_empty(self, tmp_path):
        """No beacon.yaml at the given path → returns [] (existing behavior unchanged)."""
        wh = tmp_path / "warehouse"
        wh.mkdir()
        result = get_tracked_paths(wh, wh / "no-such-beacon.yaml")
        assert result == []


class TestPer186DeletedTrackedFiles:
    """PER-186: deleted-but-tracked files must be included in expansion."""

    def test_deleted_glob_match_included(self, tmp_path):
        """Tracked file matching glob pattern, then deleted → still included."""
        import subprocess

        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        ctx_file = wh / "contexts" / "deleted.md"
        ctx_file.write_text("# Deleted\n")

        _init_git(wh)
        subprocess.run(
            ["git", "-C", str(wh), "add", "contexts/deleted.md"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )

        # Delete the file
        ctx_file.unlink()

        beacon_yaml = _write_beacon_yaml(wh, contexts=["contexts/*.md"])
        result = get_tracked_paths(wh, beacon_yaml)
        assert "contexts/deleted.md" in result, (
            f"PER-186: deleted tracked file should be included. Got: {result}"
        )

    def test_deleted_explicit_path_included(self, tmp_path):
        """Tracked explicit path, then deleted → still included."""
        import subprocess

        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        ctx_file = wh / "contexts" / "explicit.md"
        ctx_file.write_text("# Explicit\n")

        _init_git(wh)
        subprocess.run(
            ["git", "-C", str(wh), "add", "contexts/explicit.md"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )

        # Delete the file
        ctx_file.unlink()

        beacon_yaml = _write_beacon_yaml(wh, contexts=["contexts/explicit.md"])
        result = get_tracked_paths(wh, beacon_yaml)
        assert "contexts/explicit.md" in result, (
            f"PER-186: deleted explicit path should be included. Got: {result}"
        )

    def test_staged_deletion_glob_match_included(self, tmp_path):
        """Tracked file matching glob pattern, git-rm staged → still included."""
        import subprocess

        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        ctx_file = wh / "contexts" / "staged-delete.md"
        ctx_file.write_text("# Staged delete\n")

        _init_git(wh)
        subprocess.run(
            ["git", "-C", str(wh), "add", "contexts/staged-delete.md"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )

        # Stage the deletion
        subprocess.run(
            ["git", "-C", str(wh), "rm", "contexts/staged-delete.md"],
            check=True,
            capture_output=True,
        )

        beacon_yaml = _write_beacon_yaml(wh, contexts=["contexts/*.md"])
        result = get_tracked_paths(wh, beacon_yaml)
        assert "contexts/staged-delete.md" in result, (
            f"PER-186 round 2: staged-deleted tracked file should be included. Got: {result}"
        )

    def test_directory_pattern_deletion_included(self, tmp_path):
        """Directory pattern (no glob), file deleted unstaged → included."""
        import subprocess

        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        ctx_file = wh / "contexts" / "nested.md"
        ctx_file.write_text("# Nested\n")

        _init_git(wh)
        subprocess.run(
            ["git", "-C", str(wh), "add", "contexts/nested.md"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )

        # Delete the file (unstaged)
        ctx_file.unlink()

        beacon_yaml = _write_beacon_yaml(wh, contexts=["contexts/"])
        result = get_tracked_paths(wh, beacon_yaml)
        assert "contexts/nested.md" in result, (
            f"PER-186 round 2: deleted file under directory pattern should be included. Got: {result}"
        )

    def test_directory_pattern_staged_deletion_included(self, tmp_path):
        """Directory pattern (no glob), file git-rm staged → included."""
        import subprocess

        wh = tmp_path / "warehouse"
        (wh / "contexts").mkdir(parents=True)
        ctx_file = wh / "contexts" / "dir-staged.md"
        ctx_file.write_text("# Dir staged\n")

        _init_git(wh)
        subprocess.run(
            ["git", "-C", str(wh), "add", "contexts/dir-staged.md"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )

        # Stage the deletion
        subprocess.run(
            ["git", "-C", str(wh), "rm", "contexts/dir-staged.md"],
            check=True,
            capture_output=True,
        )

        beacon_yaml = _write_beacon_yaml(wh, contexts=["contexts/"])
        result = get_tracked_paths(wh, beacon_yaml)
        assert "contexts/dir-staged.md" in result, (
            f"PER-186 round 2: staged-deleted file under directory pattern should be included. Got: {result}"
        )
