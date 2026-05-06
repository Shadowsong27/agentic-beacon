"""Tests for agent manifest model and validators.

Covers tasks 1.1–1.5 from move-agent-requires-to-warehouse-manifest OpenSpec change.
"""

import pytest
import yaml
from beacon.core.dependencies.manifest import (
    MIGRATION_DOC_URL,
    AgentEntry,
    AgentManifest,
    AgentManifestError,
    load_agent_manifest,
    validate_agent_frontmatter_clean,
    validate_agents_directory,
    validate_declared_skills,
)

# ---------------------------------------------------------------------------
# 1.1 AgentManifest / AgentEntry model
# ---------------------------------------------------------------------------


class TestAgentEntryModel:
    def test_skills_default_empty(self):
        entry = AgentEntry.model_validate({})
        assert entry.skills == []

    def test_skills_explicit(self):
        entry = AgentEntry.model_validate({"skills": ["foo", "bar"]})
        assert entry.skills == ["foo", "bar"]

    def test_extra_keys_allowed(self):
        entry = AgentEntry.model_validate({"skills": [], "future_key": "value"})
        assert entry.skills == []
        assert entry.model_extra == {"future_key": "value"}

    def test_rejects_contexts_key(self):
        with pytest.raises(ValueError) as exc_info:
            AgentEntry.model_validate({"skills": [], "contexts": ["ctx"]})
        assert "contexts" in str(exc_info.value).lower()
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_rejects_contexts_none(self):
        # contexts: null should also be rejected
        with pytest.raises(ValueError) as exc_info:
            AgentEntry.model_validate({"skills": [], "contexts": None})
        assert "contexts" in str(exc_info.value).lower()

    def test_skills_must_be_list(self):
        with pytest.raises(ValueError) as exc_info:
            AgentEntry.model_validate({"skills": "not-a-list"})
        assert "list" in str(exc_info.value).lower()


class TestAgentManifestModel:
    def test_empty_manifest(self):
        manifest = AgentManifest.model_validate({"agents": {}})
        assert manifest.agents == {}

    def test_manifest_with_agents(self):
        manifest = AgentManifest.model_validate(
            {"agents": {"agent-a": {"skills": ["s1"]}, "agent-b": {"skills": []}}}
        )
        assert set(manifest.agents.keys()) == {"agent-a", "agent-b"}
        assert manifest.agents["agent-a"].skills == ["s1"]
        assert manifest.agents["agent-b"].skills == []

    def test_rejects_extra_top_level_keys(self):
        with pytest.raises(ValueError):
            AgentManifest.model_validate({"agents": {}, "bad_key": "value"})


# ---------------------------------------------------------------------------
# 1.2 load_agent_manifest
# ---------------------------------------------------------------------------


class TestLoadAgentManifest:
    def test_returns_none_when_file_missing(self, tmp_path):
        result = load_agent_manifest(tmp_path)
        assert result is None

    def test_loads_empty_mapping(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agents.yaml").write_text("", encoding="utf-8")
        result = load_agent_manifest(tmp_path)
        assert result is not None
        assert result.agents == {}

    def test_loads_valid_manifest(self, tmp_path):
        (tmp_path / "agents").mkdir()
        data = {"agent-a": {"skills": ["skill-a"]}, "agent-b": {"skills": []}}
        (tmp_path / "agents" / "agents.yaml").write_text(
            yaml.safe_dump(data), encoding="utf-8"
        )
        result = load_agent_manifest(tmp_path)
        assert result is not None
        assert result.agents["agent-a"].skills == ["skill-a"]
        assert result.agents["agent-b"].skills == []

    def test_raises_on_yaml_parse_error(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agents.yaml").write_text("bad: [", encoding="utf-8")
        with pytest.raises(AgentManifestError) as exc_info:
            load_agent_manifest(tmp_path)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_raises_on_non_dict_yaml(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agents.yaml").write_text(
            "- list_item", encoding="utf-8"
        )
        with pytest.raises(AgentManifestError) as exc_info:
            load_agent_manifest(tmp_path)
        assert "must be a YAML mapping" in str(exc_info.value)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_raises_on_schema_validation_failure(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agents.yaml").write_text(
            "agent-a:\n  contexts: [foo]", encoding="utf-8"
        )
        with pytest.raises(AgentManifestError) as exc_info:
            load_agent_manifest(tmp_path)
        assert MIGRATION_DOC_URL in str(exc_info.value)


# ---------------------------------------------------------------------------
# 1.3 validate_agents_directory
# ---------------------------------------------------------------------------


class TestValidateAgentsDirectory:
    def test_passes_when_agents_dir_empty_and_manifest_none(self, tmp_path):
        (tmp_path / "agents").mkdir()
        validate_agents_directory(tmp_path, None)

    def test_passes_when_agents_dir_empty_and_manifest_empty(self, tmp_path):
        (tmp_path / "agents").mkdir()
        manifest = AgentManifest.model_validate({"agents": {}})
        validate_agents_directory(tmp_path, manifest)

    def test_passes_when_bidirectional_match(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text("# A", encoding="utf-8")
        manifest = AgentManifest.model_validate({"agents": {"agent-a": {"skills": []}}})
        validate_agents_directory(tmp_path, manifest)

    def test_raises_when_missing_in_manifest(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text("# A", encoding="utf-8")
        manifest = AgentManifest.model_validate({"agents": {}})
        with pytest.raises(AgentManifestError) as exc_info:
            validate_agents_directory(tmp_path, manifest)
        assert "agent-a.md has no entry" in str(exc_info.value)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_raises_when_orphan_in_manifest(self, tmp_path):
        (tmp_path / "agents").mkdir()
        manifest = AgentManifest.model_validate({"agents": {"agent-a": {"skills": []}}})
        with pytest.raises(AgentManifestError) as exc_info:
            validate_agents_directory(tmp_path, manifest)
        assert "agent-a.md does not exist" in str(exc_info.value)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_raises_when_both_mismatch(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text("# A", encoding="utf-8")
        manifest = AgentManifest.model_validate({"agents": {"agent-b": {"skills": []}}})
        with pytest.raises(AgentManifestError) as exc_info:
            validate_agents_directory(tmp_path, manifest)
        assert "agent-a.md has no entry" in str(exc_info.value)
        assert "agent-b.md does not exist" in str(exc_info.value)

    def test_ignores_readme_md(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "README.md").write_text("# Readme", encoding="utf-8")
        manifest = AgentManifest.model_validate({"agents": {}})
        validate_agents_directory(tmp_path, manifest)

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.txt").write_text("text", encoding="utf-8")
        manifest = AgentManifest.model_validate({"agents": {}})
        validate_agents_directory(tmp_path, manifest)

    def test_returns_when_agents_dir_missing(self, tmp_path):
        manifest = AgentManifest.model_validate({"agents": {}})
        validate_agents_directory(tmp_path, manifest)


# ---------------------------------------------------------------------------
# 1.4 validate_agent_frontmatter_clean
# ---------------------------------------------------------------------------


class TestValidateAgentFrontmatterClean:
    def test_passes_when_no_requires(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\n---\n# Body\n", encoding="utf-8"
        )
        validate_agent_frontmatter_clean(tmp_path)

    def test_passes_when_no_frontmatter(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text("# Body\n", encoding="utf-8")
        validate_agent_frontmatter_clean(tmp_path)

    def test_raises_when_requires_present(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text(
            "---\nname: agent-a\nrequires:\n  contexts: [c]\n---\n# Body\n",
            encoding="utf-8",
        )
        with pytest.raises(AgentManifestError) as exc_info:
            validate_agent_frontmatter_clean(tmp_path)
        assert "requires:" in str(exc_info.value)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_ignores_readme_md(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "README.md").write_text(
            "---\nrequires:\n  contexts: [c]\n---\n# Readme\n", encoding="utf-8"
        )
        validate_agent_frontmatter_clean(tmp_path)

    def test_returns_when_agents_dir_missing(self, tmp_path):
        validate_agent_frontmatter_clean(tmp_path)


# ---------------------------------------------------------------------------
# 1.5 validate_declared_skills
# ---------------------------------------------------------------------------


class TestValidateDeclaredSkills:
    def test_passes_when_skills_exist(self, tmp_path):
        (tmp_path / "skills" / "skill-a").mkdir(parents=True)
        (tmp_path / "skills" / "skill-a" / "SKILL.md").write_text(
            "# Skill", encoding="utf-8"
        )
        manifest = AgentManifest.model_validate(
            {"agents": {"agent-a": {"skills": ["skill-a"]}}}
        )
        validate_declared_skills(tmp_path, manifest)

    def test_passes_when_empty_skills(self, tmp_path):
        manifest = AgentManifest.model_validate({"agents": {"agent-a": {"skills": []}}})
        validate_declared_skills(tmp_path, manifest)

    def test_raises_when_skill_missing(self, tmp_path):
        manifest = AgentManifest.model_validate(
            {"agents": {"agent-a": {"skills": ["missing-skill"]}}}
        )
        with pytest.raises(AgentManifestError) as exc_info:
            validate_declared_skills(tmp_path, manifest)
        assert "missing-skill" in str(exc_info.value)
        assert "SKILL.md" in str(exc_info.value)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_raises_when_skill_dir_exists_but_no_skill_md(self, tmp_path):
        (tmp_path / "skills" / "skill-a").mkdir(parents=True)
        manifest = AgentManifest.model_validate(
            {"agents": {"agent-a": {"skills": ["skill-a"]}}}
        )
        with pytest.raises(AgentManifestError) as exc_info:
            validate_declared_skills(tmp_path, manifest)
        assert "SKILL.md" in str(exc_info.value)

    def test_checks_all_agents(self, tmp_path):
        (tmp_path / "skills" / "skill-a").mkdir(parents=True)
        (tmp_path / "skills" / "skill-a" / "SKILL.md").write_text(
            "# Skill", encoding="utf-8"
        )
        manifest = AgentManifest.model_validate(
            {
                "agents": {
                    "agent-a": {"skills": ["skill-a"]},
                    "agent-b": {"skills": ["missing"]},
                }
            }
        )
        with pytest.raises(AgentManifestError) as exc_info:
            validate_declared_skills(tmp_path, manifest)
        assert "agent-b" in str(exc_info.value)
        assert "missing" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 1.6 Error messages contain migration URL
# ---------------------------------------------------------------------------


class TestErrorMessagesContainMigrationUrl:
    def test_load_agent_manifest_error_contains_url(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agents.yaml").write_text("bad: [", encoding="utf-8")
        with pytest.raises(AgentManifestError) as exc_info:
            load_agent_manifest(tmp_path)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_validate_agents_directory_error_contains_url(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text("# A", encoding="utf-8")
        manifest = AgentManifest.model_validate({"agents": {}})
        with pytest.raises(AgentManifestError) as exc_info:
            validate_agents_directory(tmp_path, manifest)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_validate_agent_frontmatter_clean_error_contains_url(self, tmp_path):
        (tmp_path / "agents").mkdir()
        (tmp_path / "agents" / "agent-a.md").write_text(
            "---\nrequires:\n  contexts: [c]\n---\n# Body\n", encoding="utf-8"
        )
        with pytest.raises(AgentManifestError) as exc_info:
            validate_agent_frontmatter_clean(tmp_path)
        assert MIGRATION_DOC_URL in str(exc_info.value)

    def test_validate_declared_skills_error_contains_url(self, tmp_path):
        manifest = AgentManifest.model_validate(
            {"agents": {"agent-a": {"skills": ["missing"]}}}
        )
        with pytest.raises(AgentManifestError) as exc_info:
            validate_declared_skills(tmp_path, manifest)
        assert MIGRATION_DOC_URL in str(exc_info.value)
