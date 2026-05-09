"""Unit tests for beacon.domains.distribution.artifact_listing.list_artifacts."""

from pathlib import Path

import pytest
from beacon.domains.distribution.artifact_listing import list_artifacts


@pytest.fixture
def artifacts_dir(tmp_path: Path) -> Path:
    """Minimal .agentic-beacon/artifacts/ directory with symlinks."""
    arts = tmp_path / "artifacts"
    arts.mkdir()
    return arts


def _make_symlink(link: Path, target_name: str = "real.md") -> None:
    target = link.parent / target_name
    target.write_text("content")
    link.symlink_to(target)


class TestListArtifactsDefaults:
    def test_returns_empty_dict_when_artifacts_dir_missing(
        self, tmp_path: Path
    ) -> None:
        result = list_artifacts(tmp_path / "nonexistent")
        assert result == {}

    def test_returns_empty_dict_when_sections_missing(
        self, artifacts_dir: Path
    ) -> None:
        result = list_artifacts(artifacts_dir)
        assert result == {}

    def test_default_shows_contexts_and_skills(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "contexts").mkdir()
        ctx_link = artifacts_dir / "contexts" / "AGENTS.md"
        _make_symlink(ctx_link)

        (artifacts_dir / "skills").mkdir()
        skill_link = artifacts_dir / "skills" / "SKILL.md"
        _make_symlink(skill_link)

        result = list_artifacts(artifacts_dir)

        assert "contexts" in result
        assert "skills" in result
        assert "contexts/AGENTS.md" in result["contexts"]
        assert "skills/SKILL.md" in result["skills"]

    def test_default_excludes_agents_section(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "agents").mkdir()
        _make_symlink(artifacts_dir / "agents" / "my-agent.md")

        result = list_artifacts(artifacts_dir)

        assert "agents" not in result


class TestListArtifactsFiltered:
    def test_filter_to_contexts_only(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "contexts").mkdir()
        _make_symlink(artifacts_dir / "contexts" / "python.md")
        (artifacts_dir / "skills").mkdir()
        _make_symlink(artifacts_dir / "skills" / "SKILL.md")

        result = list_artifacts(artifacts_dir, "contexts")

        assert "contexts" in result
        assert "skills" not in result

    def test_filter_to_agents(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "agents").mkdir()
        _make_symlink(artifacts_dir / "agents" / "my-agent.md")

        result = list_artifacts(artifacts_dir, "agents")

        assert "agents" in result
        assert "agents/my-agent.md" in result["agents"]

    def test_filter_to_missing_section_returns_empty(self, artifacts_dir: Path) -> None:
        result = list_artifacts(artifacts_dir, "skills")
        assert result == {}


class TestListArtifactsSymlinkFiltering:
    def test_excludes_regular_files(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "contexts").mkdir()
        (artifacts_dir / "contexts" / "regular.md").write_text("not a symlink")

        result = list_artifacts(artifacts_dir, "contexts")

        assert result == {}

    def test_excludes_dotfiles(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "contexts").mkdir()
        hidden = artifacts_dir / "contexts" / ".hidden"
        target = artifacts_dir / "contexts" / "target"
        target.write_text("x")
        hidden.symlink_to(target)

        result = list_artifacts(artifacts_dir, "contexts")

        assert result == {}

    def test_results_are_sorted(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "contexts").mkdir()
        for name in ("zzz.md", "aaa.md", "mmm.md"):
            _make_symlink(artifacts_dir / "contexts" / name, f"real_{name}")

        result = list_artifacts(artifacts_dir, "contexts")

        assert result["contexts"] == sorted(result["contexts"])

    def test_nested_symlinks_included(self, artifacts_dir: Path) -> None:
        sub = artifacts_dir / "contexts" / "python"
        sub.mkdir(parents=True)
        _make_symlink(sub / "standards.md")

        result = list_artifacts(artifacts_dir, "contexts")

        assert "contexts/python/standards.md" in result["contexts"]

    def test_paths_are_relative_to_artifacts_dir(self, artifacts_dir: Path) -> None:
        (artifacts_dir / "skills").mkdir()
        _make_symlink(artifacts_dir / "skills" / "SKILL.md")

        result = list_artifacts(artifacts_dir, "skills")

        assert all(not Path(p).is_absolute() for p in result["skills"])
