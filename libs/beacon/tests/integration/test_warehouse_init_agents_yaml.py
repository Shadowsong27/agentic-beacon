"""Integration tests for warehouse init producing valid agent manifest scaffold.

Covers task 3.4 from move-agent-requires-to-warehouse-manifest OpenSpec change.
"""

import yaml
from beacon.cli.main import main
from beacon.core.dependencies.manifest import load_agent_manifest
from click.testing import CliRunner


class TestWarehouseInitAgentsYaml:
    def test_init_creates_agents_yaml(self, tmp_path, monkeypatch):
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            main, ["warehouse", "init", "my-warehouse", "--no-git", "--no-interactive"]
        )

        assert result.exit_code == 0
        agents_yaml = tmp_path / "my-warehouse" / "agents" / "agents.yaml"
        assert agents_yaml.exists()

    def test_init_agents_yaml_is_valid_yaml(self, tmp_path, monkeypatch):
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        runner.invoke(
            main, ["warehouse", "init", "my-warehouse", "--no-git", "--no-interactive"]
        )

        agents_yaml = tmp_path / "my-warehouse" / "agents" / "agents.yaml"
        content = agents_yaml.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        # All-comment file parses to None; load_agent_manifest normalises to {}
        assert parsed is None or isinstance(parsed, dict)

    def test_init_agents_yaml_loads_as_empty_manifest(self, tmp_path, monkeypatch):
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        runner.invoke(
            main, ["warehouse", "init", "my-warehouse", "--no-git", "--no-interactive"]
        )

        wh = tmp_path / "my-warehouse"
        manifest = load_agent_manifest(wh)
        assert manifest is not None
        assert manifest.agents == {}

    def test_init_produces_warehouse_passing_status(self, tmp_path, monkeypatch):
        runner = CliRunner()
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            main, ["warehouse", "init", "my-warehouse", "--no-git", "--no-interactive"]
        )
        assert result.exit_code == 0

        wh = tmp_path / "my-warehouse"

        # Verify warehouse structure is valid
        from beacon.domains.warehouse.validator import WarehouseValidator

        validator = WarehouseValidator()
        validation = validator.validate(wh)
        assert validation.valid, f"Validation errors: {validation.errors}"
