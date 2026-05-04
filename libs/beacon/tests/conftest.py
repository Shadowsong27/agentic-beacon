"""pytest configuration and shared fixtures."""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from loguru import logger as _loguru_logger


@pytest.fixture
def loguru_caplog(caplog):
    """Bridge loguru → stdlib logging so pytest's caplog captures loguru records.

    Loguru writes to its own sinks; without this bridge, caplog.records is
    empty for any code path that emits via loguru. Tests that need to assert
    on a loguru INFO/WARNING message should depend on this fixture.
    """

    class PropagateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = _loguru_logger.add(PropagateHandler(), format="{message}")
    caplog.set_level(logging.DEBUG)
    yield caplog
    _loguru_logger.remove(handler_id)


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
  skills:
    - development/tdd-workflow.md
    - deployment/docker-compose.md
  contexts:
    - teams/backend/AGENTS.md
"""


@pytest.fixture
def sample_beacon_yaml_partial():
    """Sample partial beacon.yaml content with only skills."""
    return """
artifacts:
  skills:
    - development/tdd-workflow.md
"""


@pytest.fixture
def sample_beacon_yaml_empty():
    """Sample beacon.yaml with empty artifact lists."""
    return """
artifacts:
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

    # Initialize git repo and commit initial files (required by symlink-based sync)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }
    subprocess.run(
        ["git", "init"],
        cwd=warehouse_path,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=warehouse_path,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=warehouse_path,
        env=env,
        check=True,
        capture_output=True,
    )

    return warehouse_path
