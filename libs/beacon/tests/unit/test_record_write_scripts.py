"""Unit tests for write_knowledge.py and write_skill.py.

Both scripts are guardrails: they exist so the LLM-driven record-* skills
cannot accidentally write artifacts into the project's symlink mirror at
.agentic-beacon/artifacts/. The tests assert the warehouse-only contract.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SKILLS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "beacon" / "data" / "skills"
)


def _load_script(skill_name: str, script_name: str):
    script_path = _SKILLS_DIR / skill_name / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(
        f"{skill_name.replace('-', '_')}_{script_name.replace('.py', '')}",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_project_with_warehouse(tmp_path: Path) -> tuple[Path, Path]:
    """Create a project + sibling warehouse, wired via config.toml."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".agentic-beacon").mkdir()
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "knowledge").mkdir()
    (warehouse / "skills").mkdir()
    (project / ".agentic-beacon" / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    return project, warehouse


# ─────────────────────────────────────────────────────────────
# write_knowledge.py
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def write_knowledge():
    return _load_script("record-knowledge", "write_knowledge.py")


class TestWriteKnowledge:
    def test_writes_to_warehouse_with_flat_layout(
        self, write_knowledge, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_knowledge.py", "--type", "lesson", "--name", "foo-bar"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# Foo\nbody\n"))

        write_knowledge.main()

        target = warehouse / "knowledge" / "lessons" / "foo-bar.md"
        assert target.is_file()
        assert target.read_text() == "# Foo\nbody\n"
        out = capsys.readouterr().out.strip()
        assert out == "knowledge/lessons/foo-bar.md"

    def test_writes_to_topic_subdir_when_given(
        self, write_knowledge, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_knowledge.py",
                "--type",
                "lesson",
                "--topic",
                "infrastructure",
                "--name",
                "deploy-via-git",
            ],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# Deploy via git\n"))

        write_knowledge.main()

        target = (
            warehouse / "knowledge" / "infrastructure" / "lessons" / "deploy-via-git.md"
        )
        assert target.is_file()
        out = capsys.readouterr().out.strip()
        assert out == "knowledge/infrastructure/lessons/deploy-via-git.md"

    def test_does_not_write_to_project_artifacts(
        self, write_knowledge, tmp_path, monkeypatch
    ):
        """Regression: must never create files under project/.agentic-beacon/artifacts/."""
        project, warehouse = _make_project_with_warehouse(tmp_path)
        artifacts = project / ".agentic-beacon" / "artifacts"
        artifacts.mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_knowledge.py",
                "--type",
                "decision",
                "--name",
                "x",
            ],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# X\n"))

        write_knowledge.main()

        # Nothing landed under artifacts/
        assert list(artifacts.rglob("*")) == []
        # File is in the warehouse
        assert (warehouse / "knowledge" / "decisions" / "x.md").is_file()

    def test_refuses_to_overwrite_without_flag(
        self, write_knowledge, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        target = warehouse / "knowledge" / "lessons" / "exists.md"
        target.parent.mkdir(parents=True)
        target.write_text("OLD")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_knowledge.py", "--type", "lesson", "--name", "exists"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("NEW"))

        with pytest.raises(SystemExit) as exc:
            write_knowledge.main()
        assert exc.value.code == 3
        assert target.read_text() == "OLD"
        assert "already exists" in capsys.readouterr().err

    def test_overwrite_flag_replaces_existing(
        self, write_knowledge, tmp_path, monkeypatch
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        target = warehouse / "knowledge" / "lessons" / "exists.md"
        target.parent.mkdir(parents=True)
        target.write_text("OLD")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_knowledge.py",
                "--type",
                "lesson",
                "--name",
                "exists",
                "--overwrite",
            ],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("NEW"))

        write_knowledge.main()
        assert target.read_text() == "NEW"

    def test_rejects_non_kebab_name(
        self, write_knowledge, tmp_path, monkeypatch, capsys
    ):
        project, _ = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_knowledge.py", "--type", "lesson", "--name", "Bad_Name"],
        )
        with pytest.raises(SystemExit) as exc:
            write_knowledge.main()
        assert exc.value.code == 2
        assert "kebab-case" in capsys.readouterr().err

    def test_rejects_empty_content(
        self, write_knowledge, tmp_path, monkeypatch, capsys
    ):
        project, _ = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_knowledge.py", "--type", "lesson", "--name", "x"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("   \n"))
        with pytest.raises(SystemExit) as exc:
            write_knowledge.main()
        assert exc.value.code == 2
        assert "empty" in capsys.readouterr().err.lower()

    def test_no_warehouse_exits_nonzero(
        self, write_knowledge, tmp_path, monkeypatch, capsys
    ):
        # tmp_path has no .agentic-beacon/config.toml in its tree
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            ["write_knowledge.py", "--type", "lesson", "--name", "x"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# X\n"))
        with pytest.raises(SystemExit) as exc:
            write_knowledge.main()
        assert exc.value.code == 1
        assert "no warehouse connected" in capsys.readouterr().err

    def test_content_file_argument_works(self, write_knowledge, tmp_path, monkeypatch):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        body = tmp_path / "body.md"
        body.write_text("# From file\n")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_knowledge.py",
                "--type",
                "fact",
                "--name",
                "y",
                "--content-file",
                str(body),
            ],
        )

        write_knowledge.main()
        target = warehouse / "knowledge" / "facts" / "y.md"
        assert target.read_text() == "# From file\n"


# ─────────────────────────────────────────────────────────────
# write_context.py
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def write_context():
    return _load_script("record-knowledge", "write_context.py")


class TestWriteContext:
    def test_writes_to_warehouse_contexts(
        self, write_context, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "linear-ops"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# Linear Operations\nbody\n"))

        write_context.main()

        target = warehouse / "contexts" / "linear-ops.md"
        assert target.is_file()
        assert target.read_text() == "# Linear Operations\nbody\n"
        out = capsys.readouterr().out.strip()
        assert out == "contexts/linear-ops.md"

    def test_does_not_write_to_project_artifacts(
        self, write_context, tmp_path, monkeypatch
    ):
        """Regression: must never create files under project/.agentic-beacon/artifacts/."""
        project, warehouse = _make_project_with_warehouse(tmp_path)
        artifacts = project / ".agentic-beacon" / "artifacts"
        artifacts.mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "x"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# X\n"))

        write_context.main()

        assert list(artifacts.rglob("*")) == []
        assert (warehouse / "contexts" / "x.md").is_file()

    def test_refuses_to_overwrite_without_flag(
        self, write_context, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        target = warehouse / "contexts" / "exists.md"
        target.parent.mkdir(parents=True)
        target.write_text("OLD")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "exists"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("NEW"))

        with pytest.raises(SystemExit) as exc:
            write_context.main()
        assert exc.value.code == 3
        assert target.read_text() == "OLD"
        assert "already exists" in capsys.readouterr().err

    def test_overwrite_flag_replaces_existing(
        self, write_context, tmp_path, monkeypatch
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        target = warehouse / "contexts" / "exists.md"
        target.parent.mkdir(parents=True)
        target.write_text("OLD")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "exists", "--overwrite"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("NEW"))

        write_context.main()
        assert target.read_text() == "NEW"

    def test_rejects_non_kebab_name(self, write_context, tmp_path, monkeypatch, capsys):
        project, _ = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "Bad_Name"],
        )
        with pytest.raises(SystemExit) as exc:
            write_context.main()
        assert exc.value.code == 2
        assert "kebab-case" in capsys.readouterr().err

    def test_rejects_empty_content(self, write_context, tmp_path, monkeypatch, capsys):
        project, _ = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "x"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("   \n"))
        with pytest.raises(SystemExit) as exc:
            write_context.main()
        assert exc.value.code == 2
        assert "empty" in capsys.readouterr().err.lower()

    def test_no_warehouse_exits_nonzero(
        self, write_context, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "x"],
        )
        monkeypatch.setattr("sys.stdin", _StringStream("# X\n"))
        with pytest.raises(SystemExit) as exc:
            write_context.main()
        assert exc.value.code == 1
        assert "no warehouse connected" in capsys.readouterr().err

    def test_content_file_argument_works(self, write_context, tmp_path, monkeypatch):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        body = tmp_path / "body.md"
        body.write_text("# From file\n")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_context.py", "--name", "y", "--content-file", str(body)],
        )

        write_context.main()
        target = warehouse / "contexts" / "y.md"
        assert target.read_text() == "# From file\n"


# ─────────────────────────────────────────────────────────────
# write_skill.py
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def write_skill():
    return _load_script("record-skill", "write_skill.py")


class TestWriteSkill:
    def test_creates_skill_md_in_warehouse(
        self, write_skill, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_skill.py",
                "--name",
                "deploy-check",
                "--description",
                "Validate deployment readiness",
            ],
        )

        write_skill.main()

        skill_md = warehouse / "skills" / "deploy-check" / "SKILL.md"
        assert skill_md.is_file()
        body = skill_md.read_text()
        assert "name: deploy-check" in body
        assert "description: Validate deployment readiness" in body
        assert "/deploy-check" in body
        assert capsys.readouterr().out.strip() == "skills/deploy-check/"

    def test_does_not_write_to_project_artifacts(
        self, write_skill, tmp_path, monkeypatch
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        artifacts = project / ".agentic-beacon" / "artifacts"
        artifacts.mkdir()

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_skill.py",
                "--name",
                "x",
                "--description",
                "x",
            ],
        )

        write_skill.main()

        assert list(artifacts.rglob("*")) == []
        assert (warehouse / "skills" / "x" / "SKILL.md").is_file()

    def test_include_script_creates_pep723_scaffold(
        self, write_skill, tmp_path, monkeypatch
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_skill.py",
                "--name",
                "validate-types",
                "--description",
                "Validate Python type annotations",
                "--include-script",
            ],
        )

        write_skill.main()

        script = (
            warehouse / "skills" / "validate-types" / "scripts" / "validate-types.py"
        )
        assert script.is_file()
        content = script.read_text()
        assert content.startswith("# /// script")
        assert "requires-python" in content
        assert "validate-types" in content

    def test_requires_context_renders_into_frontmatter(
        self, write_skill, tmp_path, monkeypatch
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_skill.py",
                "--name",
                "x",
                "--description",
                "x",
                "--requires-context",
                "contexts/python-standards.md",
                "--requires-context",
                "contexts/testing.md",
            ],
        )

        write_skill.main()

        skill_md = (warehouse / "skills" / "x" / "SKILL.md").read_text()
        assert "contexts:" in skill_md
        assert "- contexts/python-standards.md" in skill_md
        assert "- contexts/testing.md" in skill_md

    def test_refuses_to_overwrite_without_flag(
        self, write_skill, tmp_path, monkeypatch, capsys
    ):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        existing = warehouse / "skills" / "exists"
        existing.mkdir(parents=True)
        (existing / "marker.txt").write_text("existing")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_skill.py", "--name", "exists", "--description", "x"],
        )

        with pytest.raises(SystemExit) as exc:
            write_skill.main()
        assert exc.value.code == 3
        assert (existing / "marker.txt").exists()  # untouched
        assert "already exists" in capsys.readouterr().err

    def test_overwrite_replaces_existing_dir(self, write_skill, tmp_path, monkeypatch):
        project, warehouse = _make_project_with_warehouse(tmp_path)
        existing = warehouse / "skills" / "exists"
        existing.mkdir(parents=True)
        (existing / "marker.txt").write_text("existing")

        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            [
                "write_skill.py",
                "--name",
                "exists",
                "--description",
                "x",
                "--overwrite",
            ],
        )

        write_skill.main()

        # Old contents gone, fresh SKILL.md present
        assert not (existing / "marker.txt").exists()
        assert (existing / "SKILL.md").is_file()

    def test_rejects_non_kebab_name(self, write_skill, tmp_path, monkeypatch, capsys):
        project, _ = _make_project_with_warehouse(tmp_path)
        monkeypatch.chdir(project)
        monkeypatch.setattr(
            "sys.argv",
            ["write_skill.py", "--name", "Bad_Name", "--description", "x"],
        )
        with pytest.raises(SystemExit) as exc:
            write_skill.main()
        assert exc.value.code == 2
        assert "kebab-case" in capsys.readouterr().err

    def test_no_warehouse_exits_nonzero(
        self, write_skill, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "sys.argv",
            ["write_skill.py", "--name", "x", "--description", "x"],
        )
        with pytest.raises(SystemExit) as exc:
            write_skill.main()
        assert exc.value.code == 1
        assert "no warehouse connected" in capsys.readouterr().err


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


class _StringStream:
    """Minimal stream-like wrapper for monkeypatching sys.stdin."""

    def __init__(self, content: str) -> None:
        self._content = content

    def read(self) -> str:
        return self._content
