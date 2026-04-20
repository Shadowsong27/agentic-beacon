"""pytest configuration and shared fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect Path.home() to a clean temp directory.

    Use this fixture in tests that invoke CLI commands which call
    detect_agents_global() or build_agents_paths(), to prevent real global
    agent installs from leaking into the test.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def beacon_dir(temp_dir):
    """Create a temporary .agentic-beacon directory."""
    beacon_path = temp_dir / ".agentic-beacon"
    beacon_path.mkdir()
    return beacon_path


@pytest.fixture
def sample_beacon_yaml_complete():
    """Sample complete beacon.yaml content."""
    return """
artifacts:
  knowledge:
    - languages/python/type-hints.md
    - languages/python/async-patterns.md
  skills:
    - development/tdd-workflow.md
    - deployment/docker-compose.md
  contexts:
    - teams/backend/AGENTS.md
"""


@pytest.fixture
def sample_beacon_yaml_partial():
    """Sample partial beacon.yaml content with only knowledge."""
    return """
artifacts:
  knowledge:
    - languages/python/basics.md
"""


@pytest.fixture
def sample_beacon_yaml_empty():
    """Sample beacon.yaml with empty artifact lists."""
    return """
artifacts:
  knowledge: []
  skills: []
  contexts: []
"""


@pytest.fixture
def sample_config_toml_valid():
    """Sample valid config.toml content."""
    return """
[warehouse]
local_path = "/absolute/path/to/warehouse"
"""


@pytest.fixture
def sample_config_toml_relative():
    """Sample config.toml with relative path."""
    return """
[warehouse]
local_path = "relative/path/to/warehouse"
"""


@pytest.fixture
def valid_warehouse(temp_dir):
    """Create a valid warehouse structure for testing."""
    warehouse_path = temp_dir / "test-warehouse"
    warehouse_path.mkdir()

    # Create required directories
    (warehouse_path / "agents").mkdir()
    (warehouse_path / "contexts").mkdir()
    (warehouse_path / "knowledge").mkdir()
    (warehouse_path / "skills").mkdir()
    (warehouse_path / "docs").mkdir()

    # Create required README
    (warehouse_path / "README.md").write_text("# Test Warehouse")

    return warehouse_path
