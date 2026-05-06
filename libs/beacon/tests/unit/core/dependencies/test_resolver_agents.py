"""Tests for dependency resolver with agent declarations (tasks 2.1–2.4)."""

from pathlib import Path

import pytest
from beacon.core.dependencies.manifest import AgentManifest, load_agent_manifest
from beacon.core.dependencies.resolver import (
    EffectiveSet,
    ResolutionFailure,
    compute_effective_set,
)
from beacon.core.exceptions import ValidationError as BeaconValidationError
from beacon.core.manifest.beacon import BeaconManifest


class TestResolverWithAgents:
    """Task 2.1: Resolver accepts declared agents and resolves their skills."""

    def _make_warehouse(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "agents").mkdir()
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

    def _write_agent_manifest(self, wh: Path, agents: dict) -> None:
        import yaml

        (wh / "agents" / "agents.yaml").write_text(yaml.dump(agents))

    def test_tc1_one_agent_one_skill(self, tmp_path):
        """TC1: One declared agent with one required skill → skill in closure."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "opsx-enhance-tasks", ["py-std"])
        self._write_context(wh, "py-std")
        self._write_agent_manifest(
            wh, {"spec-planner": {"skills": ["opsx-enhance-tasks"]}}
        )

        # Skill explicitly declared → no gap
        beacon = BeaconManifest(
            artifacts={
                "skills": ["opsx-enhance-tasks"],
                "agents": ["agents/spec-planner.md"],
            }
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "opsx-enhance-tasks" in result.skills

    def test_tc2_one_agent_empty_skills(self, tmp_path):
        """TC2: One declared agent with empty skills → no additions, no error."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent_manifest(wh, {"spec-planner": {"skills": []}})

        beacon = BeaconManifest(artifacts={"agents": ["agents/spec-planner.md"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.skills == frozenset()

    def test_tc3_two_agents_same_skill(self, tmp_path):
        """TC3: Two declared agents requiring same skill → skill appears once."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "opsx-enhance-tasks", ["py-std"])
        self._write_context(wh, "py-std")
        self._write_agent_manifest(
            wh,
            {
                "spec-planner": {"skills": ["opsx-enhance-tasks"]},
                "code-reviewer": {"skills": ["opsx-enhance-tasks"]},
            },
        )

        # Skill explicitly declared → no gap
        beacon = BeaconManifest(
            artifacts={
                "skills": ["opsx-enhance-tasks"],
                "agents": ["agents/spec-planner.md", "agents/code-reviewer.md"],
            }
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.skills == frozenset({"opsx-enhance-tasks"})

    def test_tc4_no_declared_agents(self, tmp_path):
        """TC4: No declared agents → behaves identically to pre-change baseline."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "refactor", ["py-std"])
        self._write_context(wh, "py-std")
        self._write_agent_manifest(wh, {"spec-planner": {"skills": ["refactor"]}})

        beacon = BeaconManifest(artifacts={"skills": ["refactor"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert result.skills == frozenset({"refactor"})
        assert "py-std" in result.contexts

    def test_tc5_declared_agent_missing_from_manifest(self, tmp_path):
        """TC5: Declared agent missing from agents.yaml → ResolutionFailure."""
        wh = self._make_warehouse(tmp_path)
        self._write_agent_manifest(wh, {"spec-planner": {"skills": []}})

        beacon = BeaconManifest(artifacts={"agents": ["agents/missing-agent.md"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert any("missing-agent" in e for e in result.errors)

    def test_tc6_skill_required_by_agent_not_in_beacon(self, tmp_path):
        """TC6: Agent's required skill not in beacon.yaml → ResolutionFailure with gap."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "missing-skill", [])
        self._write_agent_manifest(wh, {"spec-planner": {"skills": ["missing-skill"]}})

        beacon = BeaconManifest(artifacts={"agents": ["agents/spec-planner.md"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert result.gaps is not None
        assert any(g.missing_skill == "missing-skill" for g in result.gaps)

    def test_tc7_explicit_skill_plus_agent_skill(self, tmp_path):
        """TC7: Explicit skill + agent-required skill → both in closure."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "explicit-skill", [])
        self._write_skill(wh, "agent-skill", [])
        self._write_agent_manifest(wh, {"spec-planner": {"skills": ["agent-skill"]}})

        # Both skills explicitly declared → no gap
        beacon = BeaconManifest(
            artifacts={
                "skills": ["explicit-skill", "agent-skill"],
                "agents": ["agents/spec-planner.md"],
            }
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "explicit-skill" in result.skills
        assert "agent-skill" in result.skills

    def test_tc8_agent_path_without_prefix(self, tmp_path):
        """TC8: Agent path 'spec-planner.md' without agents/ prefix → normalises and matches."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "agent-skill", [])
        self._write_agent_manifest(wh, {"spec-planner": {"skills": ["agent-skill"]}})

        # Skill explicitly declared → no gap
        beacon = BeaconManifest(
            artifacts={"skills": ["agent-skill"], "agents": ["spec-planner.md"]}
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "agent-skill" in result.skills


class TestValidateDeclaredAgents:
    """Task 2.2: validate_declared_agents_in_manifest."""

    def test_tc1_empty_agents_returns_cleanly(self):
        """TC1: Empty artifacts.agents → no-op."""
        from beacon.core.dependencies.resolver import (
            validate_declared_agents_in_manifest,
        )

        beacon = BeaconManifest(artifacts={"agents": []})
        manifest = AgentManifest(agents={})
        validate_declared_agents_in_manifest(beacon, manifest)

    def test_tc2_all_agents_present(self):
        """TC2: All declared agents have entries → returns cleanly."""
        from beacon.core.dependencies.resolver import (
            validate_declared_agents_in_manifest,
        )

        beacon = BeaconManifest(
            artifacts={"agents": ["agents/spec-planner.md", "agents/code-reviewer.md"]}
        )
        manifest = AgentManifest(
            agents={
                "spec-planner": {"skills": []},
                "code-reviewer": {"skills": []},
            }
        )
        validate_declared_agents_in_manifest(beacon, manifest)

    def test_tc3_one_agent_missing(self):
        """TC3: One declared agent missing → raises with agent name + migration URL."""
        from beacon.core.dependencies.resolver import (
            validate_declared_agents_in_manifest,
        )

        beacon = BeaconManifest(artifacts={"agents": ["agents/missing-agent.md"]})
        manifest = AgentManifest(agents={"spec-planner": {"skills": []}})
        with pytest.raises(BeaconValidationError) as exc_info:
            validate_declared_agents_in_manifest(beacon, manifest)
        assert "missing-agent" in str(exc_info.value)
        assert "migration" in str(exc_info.value).lower()

    def test_tc4_two_agents_missing(self):
        """TC4: Two declared agents missing → raises once, lists both."""
        from beacon.core.dependencies.resolver import (
            validate_declared_agents_in_manifest,
        )

        beacon = BeaconManifest(
            artifacts={"agents": ["agents/missing-a.md", "agents/missing-b.md"]}
        )
        manifest = AgentManifest(agents={})
        with pytest.raises(BeaconValidationError) as exc_info:
            validate_declared_agents_in_manifest(beacon, manifest)
        error_str = str(exc_info.value)
        assert "missing-a" in error_str
        assert "missing-b" in error_str

    def test_tc5_bare_name_without_prefix(self):
        """TC5: Bare name without agents/ prefix → normalises and matches."""
        from beacon.core.dependencies.resolver import (
            validate_declared_agents_in_manifest,
        )

        beacon = BeaconManifest(artifacts={"agents": ["spec-planner.md"]})
        manifest = AgentManifest(agents={"spec-planner": {"skills": []}})
        validate_declared_agents_in_manifest(beacon, manifest)

    def test_tc6_malformed_agents_yaml_propagates_error(self, tmp_path):
        """TC6: agents.yaml malformed → propagates error unchanged."""
        from beacon.core.dependencies.manifest import AgentManifestError
        from beacon.core.dependencies.resolver import (
            validate_declared_agents_in_manifest,
        )

        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "agents" / "agents.yaml").write_text("not: valid: yaml: [")

        beacon = BeaconManifest(artifacts={"agents": ["agents/spec-planner.md"]})
        with pytest.raises(AgentManifestError):
            manifest = load_agent_manifest(wh)
            validate_declared_agents_in_manifest(beacon, manifest)


class TestSkillProvenance:
    """Task 2.3: Provenance tracking in closure."""

    def _make_warehouse(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "agents").mkdir()
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

    def _write_agent_manifest(self, wh: Path, agents: dict) -> None:
        import yaml

        (wh / "agents" / "agents.yaml").write_text(yaml.dump(agents))

    def test_tc1_explicit_plus_agent_provenance(self, tmp_path):
        """TC1: Skill explicit + required by agent → provenance has both."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "shared-skill", [])
        self._write_agent_manifest(wh, {"spec-planner": {"skills": ["shared-skill"]}})

        beacon = BeaconManifest(
            artifacts={"skills": ["shared-skill"], "agents": ["agents/spec-planner.md"]}
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "shared-skill" in result.skills
        # Provenance should include both explicit and agent
        assert "shared-skill" in result.skill_provenance
        prov = result.skill_provenance["shared-skill"]
        assert "explicit" in prov
        assert any("spec-planner" in p for p in prov)

    def test_tc2_agent_only_provenance(self, tmp_path):
        """TC2: Skill only required by agent → provenance is required-by-agent."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "agent-skill", [])
        self._write_agent_manifest(wh, {"spec-planner": {"skills": ["agent-skill"]}})

        # Skill explicitly declared to avoid gap; provenance still shows agent
        beacon = BeaconManifest(
            artifacts={"skills": ["agent-skill"], "agents": ["agents/spec-planner.md"]}
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        assert "agent-skill" in result.skills
        prov = result.skill_provenance["agent-skill"]
        assert "explicit" in prov
        assert any("spec-planner" in p for p in prov)

    def test_tc3_explicit_only_provenance(self, tmp_path):
        """TC3: Skill only explicit → provenance is explicit."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "explicit-skill", [])

        beacon = BeaconManifest(artifacts={"skills": ["explicit-skill"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        prov = result.skill_provenance["explicit-skill"]
        assert prov == {"explicit"}

    def test_tc4_two_agents_same_skill_provenance(self, tmp_path):
        """TC4: Two agents requiring same skill → provenance lists both."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "shared-skill", [])
        self._write_agent_manifest(
            wh,
            {
                "agent-a": {"skills": ["shared-skill"]},
                "agent-b": {"skills": ["shared-skill"]},
            },
        )

        # Skill explicitly declared to avoid gap
        beacon = BeaconManifest(
            artifacts={
                "skills": ["shared-skill"],
                "agents": ["agents/agent-a.md", "agents/agent-b.md"],
            }
        )
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, EffectiveSet)
        prov = result.skill_provenance["shared-skill"]
        assert any("agent-a" in p for p in prov)
        assert any("agent-b" in p for p in prov)

    def test_tc5_closure_ordering_deterministic(self, tmp_path):
        """TC5: Closure ordering is deterministic."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "skill-b", [])
        self._write_skill(wh, "skill-a", [])
        self._write_agent_manifest(wh, {"planner": {"skills": ["skill-b", "skill-a"]}})

        beacon = BeaconManifest(artifacts={"agents": ["agents/planner.md"]})
        result1 = compute_effective_set(beacon, wh)
        result2 = compute_effective_set(beacon, wh)
        assert result1 == result2

    def test_tc6_agent_skill_not_declared_in_beacon(self, tmp_path):
        """TC6: Skill required by agent but not in beacon.yaml → ResolutionFailure with gap."""
        wh = self._make_warehouse(tmp_path)
        self._write_skill(wh, "agent-skill", [])
        self._write_agent_manifest(wh, {"planner": {"skills": ["agent-skill"]}})

        beacon = BeaconManifest(artifacts={"agents": ["agents/planner.md"]})
        result = compute_effective_set(beacon, wh)
        assert isinstance(result, ResolutionFailure)
        assert result.gaps is not None
        assert any(g.missing_skill == "agent-skill" for g in result.gaps)
