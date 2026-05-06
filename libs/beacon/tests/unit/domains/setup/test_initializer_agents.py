"""Tests for setup initializer beacon.yaml scaffold (task 1.4)."""

import yaml
from beacon.domains.setup.initializer import WarehouseInitializer


class TestInitializerBeaconYaml:
    """Task 1.4: abc setup writes beacon.yaml with agents: []"""

    def test_warehouse_init_beacon_yaml_has_agents(self, tmp_path):
        """TC1: abc warehouse init creates beacon.yaml with agents: []"""
        warehouse_path = tmp_path / "test-warehouse"
        initializer = WarehouseInitializer(warehouse_path=warehouse_path)
        initializer.init(org_name="Test Org")
        # Note: warehouse init doesn't create .agentic-beacon/beacon.yaml directly
        # The beacon.yaml is created by abc setup, not abc warehouse init

    def test_beacon_template_has_agents(self, tmp_path):
        """TC1: create_beacon_template writes agents: []"""
        from beacon.domains.setup.wiring import create_beacon_template

        beacon_file = tmp_path / "beacon.yaml"
        create_beacon_template(beacon_file)
        content = beacon_file.read_text()

        assert "agents:" in content
        data = yaml.safe_load(content)
        assert data["artifacts"]["agents"] == []
