"""Tests for warehouse status with agents (tasks 6.1–6.3)."""

import yaml
from beacon.domains.warehouse.validator import WarehouseValidator


class TestWarehouseValidatorAgents:
    """Task 6.1: Warehouse validator reports agent skill issues."""

    def test_validator_reports_missing_agent_skill(self, tmp_path):
        """TC1: Warehouse with agent declaring missing skill → validation fails."""
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "docs").mkdir()
        (wh / ".git").mkdir()
        (wh / "README.md").write_text("# Warehouse\n")

        # Agent manifest declares a skill that doesn't exist
        (wh / "agents" / "agents.yaml").write_text(
            yaml.dump({"planner": {"skills": ["missing-skill"]}})
        )
        (wh / "agents" / "planner.md").write_text("# Agent\n")

        validator = WarehouseValidator()
        result = validator.validate(wh)

        assert not result.valid
        assert any("missing-skill" in e for e in result.errors)

    def test_validator_passes_when_all_agent_skills_exist(self, tmp_path):
        """TC2: Warehouse with agent skills present → validation passes."""
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "docs").mkdir()
        (wh / ".git").mkdir()
        (wh / "README.md").write_text("# Warehouse\n")

        # Create the skill
        skill_dir = wh / "skills" / "existing-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill\n")

        (wh / "agents" / "agents.yaml").write_text(
            yaml.dump({"planner": {"skills": ["existing-skill"]}})
        )
        (wh / "agents" / "planner.md").write_text("# Agent\n")

        validator = WarehouseValidator()
        result = validator.validate(wh)

        assert result.valid is True
