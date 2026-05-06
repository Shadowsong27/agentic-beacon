"""Unit tests for the migrate-agent-requires.py script.

Covers task 4.2 from move-agent-requires-to-warehouse-manifest OpenSpec change.
"""

import subprocess
import sys
from pathlib import Path

import yaml

# The script is not importable as a module, so we invoke it via subprocess.
MIGRATE_SCRIPT = Path(__file__).parents[4] / "scripts" / "migrate-agent-requires.py"


def _run_script(warehouse_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MIGRATE_SCRIPT), str(warehouse_path)],
        capture_output=True,
        text=True,
    )


def _make_warehouse(tmp_path: Path) -> Path:
    wh = tmp_path / "warehouse"
    (wh / "agents").mkdir(parents=True)
    return wh


class TestMigrationScript:
    def test_migrates_agent_with_skills_and_contexts(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\nrequires:\n  contexts: [ctx-a]\n  skills: [skill-a]\n---\n# Body\n",
            encoding="utf-8",
        )

        result = _run_script(wh)
        assert result.returncode == 0, result.stderr

        # agents.yaml should contain skills only
        agents_yaml = wh / "agents" / "agents.yaml"
        assert agents_yaml.exists()
        manifest = yaml.safe_load(agents_yaml.read_text(encoding="utf-8"))
        assert manifest == {"agent-a": {"skills": ["skill-a"]}}

        # Agent file should have requires stripped
        agent_file = wh / "agents" / "agent-a.md"
        content = agent_file.read_text(encoding="utf-8")
        assert "requires:" not in content
        assert "name: agent-a" in content
        assert "# Body" in content

    def test_migrates_agent_with_skills_only(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-b.md").write_text(
            "---\nname: agent-b\nrequires:\n  skills: [skill-b]\n---\n# Body\n",
            encoding="utf-8",
        )

        result = _run_script(wh)
        assert result.returncode == 0, result.stderr

        manifest = yaml.safe_load(
            (wh / "agents" / "agents.yaml").read_text(encoding="utf-8")
        )
        assert manifest == {"agent-b": {"skills": ["skill-b"]}}

    def test_leaves_agent_without_requires_unchanged(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-c.md").write_text(
            "---\nname: agent-c\n---\n# Body\n", encoding="utf-8"
        )

        result = _run_script(wh)
        assert result.returncode == 0, result.stderr

        manifest = yaml.safe_load(
            (wh / "agents" / "agents.yaml").read_text(encoding="utf-8")
        )
        assert manifest == {}

        content = (wh / "agents" / "agent-c.md").read_text(encoding="utf-8")
        assert "name: agent-c" in content

    def test_idempotent_second_run(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\nrequires:\n  skills: [skill-a]\n---\n# Body\n",
            encoding="utf-8",
        )

        result1 = _run_script(wh)
        assert result1.returncode == 0, result1.stderr

        result2 = _run_script(wh)
        assert result2.returncode == 0, result2.stderr
        assert "already exists" in result2.stdout

        # Should still be valid
        manifest = yaml.safe_load(
            (wh / "agents" / "agents.yaml").read_text(encoding="utf-8")
        )
        assert manifest == {"agent-a": {"skills": ["skill-a"]}}

    def test_errors_when_agents_yaml_exists_and_differs(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\nrequires:\n  skills: [skill-a]\n---\n# Body\n",
            encoding="utf-8",
        )
        # Pre-create agents.yaml with different content
        (wh / "agents" / "agents.yaml").write_text(
            yaml.safe_dump({"other-agent": {"skills": []}}), encoding="utf-8"
        )

        result = _run_script(wh)
        assert result.returncode == 1
        assert "already exists and differs" in result.stderr

    def test_prints_summary_of_dropped_contexts(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\nrequires:\n  contexts: [ctx-a, ctx-b]\n  skills: [skill-a]\n---\n# Body\n",
            encoding="utf-8",
        )

        result = _run_script(wh)
        assert result.returncode == 0, result.stderr
        assert "Dropped contexts" in result.stdout or "dropped" in result.stdout.lower()
        assert "ctx-a" in result.stdout
        assert "ctx-b" in result.stdout

    def test_ignores_readme_md(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "README.md").write_text(
            "---\nrequires:\n  contexts: [ctx]\n  skills: [skill]\n---\n# Readme\n",
            encoding="utf-8",
        )

        result = _run_script(wh)
        assert result.returncode == 0, result.stderr

        manifest = yaml.safe_load(
            (wh / "agents" / "agents.yaml").read_text(encoding="utf-8")
        )
        assert manifest == {}

    def test_migrates_multiple_agents(self, tmp_path):
        wh = _make_warehouse(tmp_path)
        (wh / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\nrequires:\n  skills: [skill-a]\n---\n# A\n",
            encoding="utf-8",
        )
        (wh / "agents" / "agent-b.md").write_text(
            "---\nname: agent-b\nrequires:\n  contexts: [ctx-b]\n---\n# B\n",
            encoding="utf-8",
        )
        (wh / "agents" / "agent-c.md").write_text(
            "---\nname: agent-c\n---\n# C\n", encoding="utf-8"
        )

        result = _run_script(wh)
        assert result.returncode == 0, result.stderr

        manifest = yaml.safe_load(
            (wh / "agents" / "agents.yaml").read_text(encoding="utf-8")
        )
        assert manifest == {
            "agent-a": {"skills": ["skill-a"]},
            "agent-b": {"skills": []},
        }

        # Check stripped files
        assert "requires:" not in (wh / "agents" / "agent-a.md").read_text(
            encoding="utf-8"
        )
        assert "requires:" not in (wh / "agents" / "agent-b.md").read_text(
            encoding="utf-8"
        )
        assert "name: agent-c" in (wh / "agents" / "agent-c.md").read_text(
            encoding="utf-8"
        )
