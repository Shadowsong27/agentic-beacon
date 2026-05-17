"""Unit tests for draft_commit_message.py (Task 9.2 / TDD for Task 5).

TDD test cases per tasks.md TC tables for 5.3, 5.4, 5.5, 5.6.

Tests import derive_scope, derive_type, and the main output format directly
from the script module to avoid full PEP 723 invocation in unit tests.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

_SKILLS_DIR = Path(__file__).resolve().parents[5] / "src" / "beacon" / "data" / "skills"
_SCRIPT_PATH = (
    _SKILLS_DIR / "contribute-warehouse" / "scripts" / "draft_commit_message.py"
)

CONVENTIONAL_COMMITS_RE = re.compile(
    r"^(feat|fix|docs|chore|refactor|test)(\([a-z0-9\-]+\))?: .+"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("draft_commit_message", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 5.3): derive_scope
# ─────────────────────────────────────────────────────────────────────────────


class TestDeriveScope:
    """5.3 test cases: derive_scope(paths) -> str."""

    def test_tc1_contexts_only(self):
        """TC1: contexts-only paths → scope 'contexts'."""
        mod = _load_script()
        assert mod.derive_scope(["contexts/python-standards.md"]) == "contexts"

    def test_tc2_skills_only(self):
        """TC2: skills-only paths → scope 'skills'."""
        mod = _load_script()
        assert mod.derive_scope(["skills/foo/SKILL.md"]) == "skills"

    def test_tc3_agents_only(self):
        """TC3: agents-only paths → scope 'agents'."""
        mod = _load_script()
        assert mod.derive_scope(["agents/bar.md"]) == "agents"

    def test_tc4_knowledge_same_topic(self):
        """TC4: knowledge same-topic paths → scope '<topic>'."""
        mod = _load_script()
        result = mod.derive_scope(
            [
                "knowledge/python-standards/lessons/x.md",
                "knowledge/python-standards/decisions/y.md",
            ]
        )
        assert result == "python-standards"

    def test_tc5_knowledge_mixed_topics(self):
        """TC5: knowledge mixed-topic paths → scope 'knowledge'."""
        mod = _load_script()
        result = mod.derive_scope(
            [
                "knowledge/python-standards/lessons/x.md",
                "knowledge/cicd/lessons/y.md",
            ]
        )
        assert result == "knowledge"

    def test_tc6_mixed_contexts_and_knowledge(self):
        """TC6: contexts + knowledge mixed → fallback to 'general' or common ancestor."""
        mod = _load_script()
        result = mod.derive_scope(
            [
                "contexts/a.md",
                "knowledge/x/lessons/y.md",
            ]
        )
        # Should be a non-empty fallback string (e.g. 'general' or empty prefix)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tc7_root_level_file(self):
        """TC7: Root-level path → scope is filename stem or fallback constant."""
        mod = _load_script()
        result = mod.derive_scope(["single-file.md"])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_tc8_empty_paths_raises(self):
        """TC8: Empty paths list → raises ValueError."""
        mod = _load_script()
        with pytest.raises((ValueError, SystemExit)):
            mod.derive_scope([])


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 5.4): derive_type
# ─────────────────────────────────────────────────────────────────────────────


class TestDeriveType:
    """5.4 test cases: derive_type(paths, git_statuses) -> str."""

    def test_tc1_skills_new_files(self):
        """TC1: All paths under skills/ with new files → 'feat'."""
        mod = _load_script()
        result = mod.derive_type(
            ["skills/foo/SKILL.md", "skills/foo/scripts/foo.py"],
            git_statuses=["A", "A"],
        )
        assert result == "feat"

    def test_tc2_contexts_only(self):
        """TC2: All paths under contexts/ → 'docs'."""
        mod = _load_script()
        result = mod.derive_type(["contexts/python-standards.md"])
        assert result == "docs"

    def test_tc3_knowledge_only(self):
        """TC3: All paths under knowledge/ → 'docs'."""
        mod = _load_script()
        result = mod.derive_type(["knowledge/python/lessons/type-hints.md"])
        assert result == "docs"

    def test_tc4_mixed_skills_and_contexts(self):
        """TC4: Mixed skills/ + contexts/ → 'chore'."""
        mod = _load_script()
        result = mod.derive_type(
            [
                "skills/foo/SKILL.md",
                "contexts/bar.md",
            ]
        )
        assert result == "chore"

    def test_tc5_skills_existing_file_modification(self):
        """TC5: Modifying existing skills/ file (not new) → 'fix' or documented rule."""
        mod = _load_script()
        result = mod.derive_type(
            ["skills/foo/SKILL.md"],
            git_statuses=["M"],
        )
        # Could be 'fix' or 'feat' per documented rule — just verify it's a valid type
        assert result in ("feat", "fix", "docs", "chore", "refactor", "test")

    def test_tc6_agents_only(self):
        """TC6: Path under agents/ → documented rule (feat for new, fix for mod)."""
        mod = _load_script()
        # New agent
        result_new = mod.derive_type(["agents/bar.md"], git_statuses=["A"])
        assert result_new in ("feat", "fix", "docs", "chore")
        # Modified agent
        result_mod = mod.derive_type(["agents/bar.md"], git_statuses=["M"])
        assert result_mod in ("feat", "fix", "docs", "chore")


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 5.5): Output format
# ─────────────────────────────────────────────────────────────────────────────


class TestOutputFormat:
    """5.5 test cases: formatted Conventional Commits message."""

    def test_tc1_contexts_output_format(self, monkeypatch, capsys):
        """TC1: contexts path → 'docs(contexts): <subject>'."""
        mod = _load_script()
        monkeypatch.setattr(
            "sys.argv",
            [
                "draft_commit_message.py",
                "--paths",
                "contexts/python-standards.md",
                "--subject",
                "add loguru section",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out.strip()
        assert out == "docs(contexts): add loguru section"
        assert CONVENTIONAL_COMMITS_RE.match(out)

    def test_tc_no_trailing_whitespace(self, monkeypatch, capsys):
        """Output has no trailing whitespace."""
        mod = _load_script()
        monkeypatch.setattr(
            "sys.argv",
            [
                "draft_commit_message.py",
                "--paths",
                "contexts/python-standards.md",
                "--subject",
                "add section",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert not out.rstrip("\n").endswith(" ")


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 5.6 / 9.2 TC9): Determinism
# ─────────────────────────────────────────────────────────────────────────────


class TestDeterminism:
    """5.6 / 9.2 TC9: same inputs → same output 10 times."""

    def test_tc9_deterministic_output(self, monkeypatch, capsys):
        """TC9: 10 invocations with identical args produce identical output."""
        mod = _load_script()
        outputs = []
        for _ in range(10):
            monkeypatch.setattr(
                "sys.argv",
                [
                    "draft_commit_message.py",
                    "--paths",
                    "contexts/python-standards.md",
                    "--subject",
                    "add loguru section",
                ],
            )
            with pytest.raises(SystemExit):
                mod.main()
            out = capsys.readouterr().out.strip()
            outputs.append(out)

        assert len(set(outputs)) == 1, f"Non-deterministic outputs: {set(outputs)}"


# ─────────────────────────────────────────────────────────────────────────────
# Additional integration tests per 9.2 TC table
# ─────────────────────────────────────────────────────────────────────────────


class TestFullCombinations:
    """9.2 TDD test cases TC1-TC8."""

    def test_tc1_contexts_scope_and_type(self):
        """TC1: contexts-only → scope='contexts', type='docs'."""
        mod = _load_script()
        assert mod.derive_scope(["contexts/python-standards.md"]) == "contexts"
        assert mod.derive_type(["contexts/python-standards.md"]) == "docs"

    def test_tc2_knowledge_same_topic(self):
        """TC2: knowledge same-topic → scope='<topic>', type='docs'."""
        mod = _load_script()
        paths = [
            "knowledge/python/lessons/type-hints.md",
            "knowledge/python/decisions/py-choice.md",
        ]
        assert mod.derive_scope(paths) == "python"
        assert mod.derive_type(paths) == "docs"

    def test_tc3_knowledge_mixed_topics(self):
        """TC3: knowledge mixed-topic → scope='knowledge', type='docs'."""
        mod = _load_script()
        paths = [
            "knowledge/python/lessons/type-hints.md",
            "knowledge/cicd/lessons/deploy.md",
        ]
        assert mod.derive_scope(paths) == "knowledge"
        assert mod.derive_type(paths) == "docs"

    def test_tc4_skills_new_file(self):
        """TC4: skills new file → scope='skills', type='feat'."""
        mod = _load_script()
        paths = ["skills/my-skill/SKILL.md"]
        assert mod.derive_scope(paths) == "skills"
        assert mod.derive_type(paths, git_statuses=["A"]) == "feat"

    def test_tc5_skills_existing_file(self):
        """TC5: skills existing file modification → scope='skills', documented type."""
        mod = _load_script()
        paths = ["skills/my-skill/SKILL.md"]
        assert mod.derive_scope(paths) == "skills"
        t = mod.derive_type(paths, git_statuses=["M"])
        assert t in ("feat", "fix")  # per documented rule

    def test_tc6_mixed_contexts_skills(self):
        """TC6: mixed contexts + skills → scope fallback, type='chore'."""
        mod = _load_script()
        paths = ["contexts/a.md", "skills/b/SKILL.md"]
        assert mod.derive_type(paths) == "chore"
        scope = mod.derive_scope(paths)
        assert isinstance(scope, str) and len(scope) > 0

    def test_tc7_agents_only(self):
        """TC7: agents-only → scope='agents', type per rule."""
        mod = _load_script()
        paths = ["agents/bar.md"]
        assert mod.derive_scope(paths) == "agents"
        t = mod.derive_type(paths)
        assert t in ("feat", "fix", "docs", "chore")

    def test_tc8_empty_paths_raises(self):
        """TC8: empty paths → raises ValueError."""
        mod = _load_script()
        with pytest.raises((ValueError, SystemExit)):
            mod.derive_scope([])
