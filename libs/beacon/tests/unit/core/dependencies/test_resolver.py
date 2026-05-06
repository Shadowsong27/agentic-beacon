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
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "knowledge").mkdir()
        return wh

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
        """TC1: Empty manifest -> all three sets empty."""
        wh = self._make_warehouse(tmp_path)
        beacon = BeaconManifest(artifacts={})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.contexts == frozenset()
        assert result.skills == frozenset()
        assert result.knowledge == frozenset()

    def test_tc2_explicit_context(self, tmp_path):
        """TC2: One explicit context -> contexts={that}, knowledge from scan."""
        wh = self._make_warehouse(tmp_path)
        self._write_context(wh, "py-std", "[x](../knowledge/py.md)\n")
        beacon = BeaconManifest(artifacts={"contexts": ["py-std"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.contexts == frozenset({"py-std"})
        assert result.skills == frozenset()
        assert result.knowledge == frozenset({"knowledge/py.md"})

    def test_tc3_skill_requires_context(self, tmp_path):
        """TC3: Explicit skill requiring context -> context included transitively."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "refactor", ["py-std"])
        self._write_context(wh, "py-std")
        beacon = BeaconManifest(artifacts={"skills": ["refactor"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "py-std" in result.contexts
        assert result.explicit_contexts == frozenset()

    def test_tc4_shared_knowledge_file(self, tmp_path):
        """TC4: Two contexts sharing a knowledge file -> knowledge set has one entry."""
        wh = self._make_warehouse(tmp_path)
        self._write_context(wh, "a", "[x](../knowledge/shared.md)\n")
        self._write_context(wh, "b", "[x](../knowledge/shared.md)\n")
        beacon = BeaconManifest(artifacts={"contexts": ["a", "b"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.knowledge == frozenset({"knowledge/shared.md"})

    def test_tc5_explicit_plus_transitive_context(self, tmp_path):
        """TC5: Explicit context plus skill requiring same context -> explicit wins."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "refactor", ["py-std"])
        self._write_context(wh, "py-std")
        beacon = BeaconManifest(
            artifacts={"skills": ["refactor"], "contexts": ["py-std"]}
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "py-std" in result.contexts
        assert "py-std" in result.explicit_contexts

    def test_tc6_explicit_skill_unreferenced(self, tmp_path):
        """TC6: Explicit skill -> included, pulls its contexts."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "refactor", ["py-std"])
        self._write_context(wh, "py-std")
        beacon = BeaconManifest(artifacts={"skills": ["refactor"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.skills == frozenset({"refactor"})
        assert "py-std" in result.contexts

    def test_tc7_missing_skill_context(self, tmp_path):
        """TC7: Skill requiring context missing from warehouse -> structured failure with skill name."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "refactor", ["missing"])
        beacon = BeaconManifest(artifacts={"skills": ["refactor"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert any("missing" in e for e in result.errors)
        assert any("refactor" in e for e in result.errors)

    def test_tc8_agents_artifact_type_accepted(self, tmp_path):
        """TC8: beacon.yaml with agents key -> accepted (agents is a valid type)."""
        manifest = BeaconManifest(artifacts={"agents": ["reviewer"]})
        assert manifest.artifacts.agents == ["reviewer"]

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
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        return wh

    def test_tc1_missing_skill_in_warehouse(self, tmp_path):
        """TC1: Skill not found in warehouse -> failure with 1 error."""
        wh = self._make_warehouse(tmp_path)
        beacon = BeaconManifest(artifacts={"skills": ["missing-skill"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert len(result.errors) == 1
        assert "missing-skill" in result.errors[0]

    def test_tc2_missing_context_for_skill(self, tmp_path):
        """TC2: Skill requires context that doesn't exist -> failure with 1 error naming the skill."""
        wh = self._make_warehouse(tmp_path)

        skill_dir = wh / "skills" / "refactor"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  contexts: [missing-ctx]\n---\n"
        )

        beacon = BeaconManifest(artifacts={"skills": ["refactor"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert len(result.errors) == 1
        assert "missing-ctx" in result.errors[0]
        assert "refactor" in result.errors[0]

    def test_tc3_missing_adopted_context_in_warehouse(self, tmp_path):
        """TC3: Explicit context not in warehouse -> failure."""
        wh = self._make_warehouse(tmp_path)
        beacon = BeaconManifest(artifacts={"contexts": ["missing"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert any("missing" in e for e in result.errors)


class TestIsTransitivelyRequired:
    """Task 6.7: is_transitively_required — TDD test cases."""

    def _make_eff(self, contexts, skills, explicit_contexts, explicit_skills):
        provenance = {}
        for skill in skills:
            if skill in explicit_skills:
                provenance[skill] = frozenset({"explicit"})
            else:
                provenance[skill] = frozenset()
        return EffectiveSet(
            contexts=frozenset(contexts),
            skills=frozenset(skills),
            knowledge=frozenset(),
            explicit_contexts=frozenset(explicit_contexts),
            explicit_skills=frozenset(explicit_skills),
            skill_provenance=provenance,
        )

    def test_tc1_explicit_context(self):
        """TC1: Context in explicit list -> False."""
        es = self._make_eff({"a"}, set(), {"a"}, set())
        assert is_transitively_required("a", es) is False

    def test_tc2_transitive_context(self):
        """TC2: Context in effective set but not explicit list -> True."""
        es = self._make_eff({"a"}, set(), set(), set())
        assert is_transitively_required("a", es) is True

    def test_tc3_explicit_and_transitive(self):
        """TC3: Context in both (explicit + required by skill) -> False (explicit wins)."""
        es = self._make_eff({"a"}, set(), {"a"}, set())
        assert is_transitively_required("a", es) is False

    def test_tc4_neither(self):
        """TC4: Context in neither -> False."""
        es = self._make_eff(set(), set(), set(), set())
        assert is_transitively_required("a", es) is False

    def test_skill_transitive(self):
        """Skill in effective set but not explicit -> True."""
        es = self._make_eff(set(), {"s"}, set(), set())
        assert is_transitively_required("s", es) is True

    def test_skill_explicit(self):
        """Skill in explicit list -> False."""
        es = self._make_eff(set(), {"s"}, set(), {"s"})
        assert is_transitively_required("s", es) is False
