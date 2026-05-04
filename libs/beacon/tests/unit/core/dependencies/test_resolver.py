"""Tests for the dependency resolver (tasks 6.1–6.8).

Covers all TDD test cases listed under each task in the auto-pull-artifact-dependencies
OpenSpec change.
"""

from pathlib import Path

from beacon.core.dependencies.resolver import (
    EffectiveSet,
    ResolutionFailure,
    compute_effective_set,
    is_transitively_required,
)
from beacon.core.manifest.beacon import BeaconManifest


class TestComputeEffectiveSet:
    """Task 6.2: compute_effective_set — TDD test cases."""

    def _make_warehouse(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "knowledge").mkdir()
        return wh

    def _write_agent(
        self, wh: Path, name: str, contexts: list[str], skills: list[str]
    ) -> None:
        content = "---\n"
        content += f"requires:\n  contexts: {contexts}\n  skills: {skills}\n"
        content += "---\n# Agent\n"
        (wh / "agents" / f"{name}.md").write_text(content)

    def _write_skill(self, wh: Path, name: str, contexts: list[str]) -> None:
        content = "---\n"
        content += f"requires:\n  contexts: {contexts}\n"
        content += "---\n# Skill\n"
        skill_dir = wh / "skills" / name
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content)

    def _write_context(self, wh: Path, name: str, body: str = "# Context\n") -> None:
        (wh / "contexts" / f"{name}.md").write_text(body)

    def test_tc1_empty_manifest(self, tmp_path):
        """TC1: Empty manifest → all three sets empty."""
        wh = self._make_warehouse(tmp_path)
        beacon = BeaconManifest(artifacts={})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.contexts == frozenset()
        assert result.skills == frozenset()
        assert result.knowledge == frozenset()

    def test_tc2_explicit_context_no_agent(self, tmp_path):
        """TC2: One explicit context, no agent → contexts={that}, knowledge from scan."""
        wh = self._make_warehouse(tmp_path)
        self._write_context(wh, "py-std", "[x](../knowledge/py.md)\n")
        beacon = BeaconManifest(artifacts={"contexts": ["py-std"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.contexts == frozenset({"py-std"})
        assert result.skills == frozenset()
        assert result.knowledge == frozenset({"knowledge/py.md"})

    def test_tc3_agent_requires_context(self, tmp_path):
        """TC3: One agent requiring one context → context included transitively."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["py-std"], [])
        self._write_context(wh, "py-std")
        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "py-std" in result.contexts
        assert result.explicit_contexts == frozenset()

    def test_tc4_chained_agent_skill_context(self, tmp_path):
        """TC4: Chained agent→skill→context → all three tiers populated."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["py-std"], ["refactor"])
        self._write_skill(wh, "refactor", ["testing"])
        self._write_context(wh, "py-std")
        self._write_context(wh, "testing")
        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.contexts == frozenset({"py-std", "testing"})
        assert result.skills == frozenset({"refactor"})

    def test_tc5_shared_knowledge_file(self, tmp_path):
        """TC5: Two contexts sharing a knowledge file → knowledge set has one entry."""
        wh = self._make_warehouse(tmp_path)
        self._write_context(wh, "a", "[x](../knowledge/shared.md)\n")
        self._write_context(wh, "b", "[x](../knowledge/shared.md)\n")
        beacon = BeaconManifest(artifacts={"contexts": ["a", "b"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.knowledge == frozenset({"knowledge/shared.md"})

    def test_tc6_explicit_plus_transitive_context(self, tmp_path):
        """TC6: Explicit context plus agent requiring same context → explicit wins."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["py-std"], [])
        self._write_context(wh, "py-std")
        beacon = BeaconManifest(
            artifacts={"agents": ["reviewer"], "contexts": ["py-std"]}
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "py-std" in result.contexts
        assert "py-std" in result.explicit_contexts

    def test_tc7_explicit_skill_unreferenced(self, tmp_path):
        """TC7: Explicit skill unreferenced by any agent → included, pulls its contexts."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "refactor", ["py-std"])
        self._write_context(wh, "py-std")
        beacon = BeaconManifest(artifacts={"skills": ["refactor"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.skills == frozenset({"refactor"})
        assert "py-std" in result.contexts

    def test_tc8_missing_context(self, tmp_path):
        """TC8: Agent requiring non-existent context → structured failure."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["missing"], [])
        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert any("missing" in e for e in result.errors)

    def test_idempotent(self, tmp_path):
        """Calling twice with same inputs yields equal results."""
        wh = self._make_warehouse(tmp_path)
        self._write_context(wh, "a")
        beacon = BeaconManifest(artifacts={"contexts": ["a"]})
        r1 = compute_effective_set(beacon, wh)
        r2 = compute_effective_set(beacon, wh)
        assert r1 == r2


class TestMissingDepErrors:
    """Task 6.6: Collect missing-dependency errors — TDD test cases."""

    def _make_warehouse(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        return wh

    def _write_agent(
        self, wh: Path, name: str, contexts: list[str], skills: list[str]
    ) -> None:
        content = "---\n"
        content += f"requires:\n  contexts: {contexts}\n  skills: {skills}\n"
        content += "---\n# Agent\n"
        (wh / "agents" / f"{name}.md").write_text(content)

    def test_tc1_single_missing_context(self, tmp_path):
        """TC1: Single missing context → failure with 1 error."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["missing"], [])
        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert len(result.errors) == 1
        assert "missing" in result.errors[0]

    def test_tc2_two_missing_contexts_same_agent(self, tmp_path):
        """TC2: Two missing contexts in same agent → failure with 2 errors."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["a", "b"], [])
        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert len(result.errors) == 2
        assert any("a" in e for e in result.errors)
        assert any("b" in e for e in result.errors)

    def test_tc3_missing_context_and_skill(self, tmp_path):
        """TC3: Missing context and missing skill in same agent → 2 errors."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent(wh, "reviewer", ["missing-ctx"], ["missing-skill"])
        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert len(result.errors) == 2
        assert any("missing-ctx" in e for e in result.errors)
        assert any("missing-skill" in e for e in result.errors)

    def test_tc4_transitive_skill_missing_context(self, tmp_path):
        """TC4: Missing context required by transitively-pulled skill → 1 error."""
        wh = self._make_warehouse(tmp_path)

        agent_file = wh / "agents" / "reviewer.md"
        agent_file.write_text(
            "---\nrequires:\n  contexts: []\n  skills: [refactor]\n---\n"
        )

        skill_dir = wh / "skills" / "refactor"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  contexts: [missing-ctx]\n---\n"
        )

        beacon = BeaconManifest(artifacts={"agents": ["reviewer"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert len(result.errors) == 1
        assert "missing-ctx" in result.errors[0]


class TestIsTransitivelyRequired:
    """Task 6.7: is_transitively_required — TDD test cases."""

    def test_tc1_explicit_context(self):
        """TC1: Context in explicit list → False."""
        es = EffectiveSet(
            contexts=frozenset({"a"}),
            skills=frozenset(),
            knowledge=frozenset(),
            explicit_contexts=frozenset({"a"}),
            explicit_skills=frozenset(),
            explicit_agents=frozenset(),
        )
        assert is_transitively_required("a", es) is False

    def test_tc2_transitive_context(self):
        """TC2: Context in effective set but not explicit list → True."""
        es = EffectiveSet(
            contexts=frozenset({"a"}),
            skills=frozenset(),
            knowledge=frozenset(),
            explicit_contexts=frozenset(),
            explicit_skills=frozenset(),
            explicit_agents=frozenset(),
        )
        assert is_transitively_required("a", es) is True

    def test_tc3_explicit_and_transitive(self):
        """TC3: Context in both (explicit + required by agent) → False (explicit wins)."""
        es = EffectiveSet(
            contexts=frozenset({"a"}),
            skills=frozenset(),
            knowledge=frozenset(),
            explicit_contexts=frozenset({"a"}),
            explicit_skills=frozenset(),
            explicit_agents=frozenset(),
        )
        assert is_transitively_required("a", es) is False

    def test_tc4_neither(self):
        """TC4: Context in neither → False."""
        es = EffectiveSet(
            contexts=frozenset(),
            skills=frozenset(),
            knowledge=frozenset(),
            explicit_contexts=frozenset(),
            explicit_skills=frozenset(),
            explicit_agents=frozenset(),
        )
        assert is_transitively_required("a", es) is False

    def test_skill_transitive(self):
        """Skill in effective set but not explicit → True."""
        es = EffectiveSet(
            contexts=frozenset(),
            skills=frozenset({"s"}),
            knowledge=frozenset(),
            explicit_contexts=frozenset(),
            explicit_skills=frozenset(),
            explicit_agents=frozenset(),
        )
        assert is_transitively_required("s", es) is True

    def test_skill_explicit(self):
        """Skill in explicit list → False."""
        es = EffectiveSet(
            contexts=frozenset(),
            skills=frozenset({"s"}),
            knowledge=frozenset(),
            explicit_contexts=frozenset(),
            explicit_skills=frozenset({"s"}),
            explicit_agents=frozenset(),
        )
        assert is_transitively_required("s", es) is False
