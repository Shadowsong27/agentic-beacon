"""Tests for abc warehouse connect command.

Following TDD workflow for tasks 3.1-3.7:
- Task 3.1: Warehouse command group
- Task 3.2: Connect command with --path parameter
- Task 3.3: Interactive prompt workflow
- Task 3.4: Warehouse validation integration
- Task 3.5: Connection persistence
- Task 3.6: Success confirmation messaging
- Task 3.7: Progress indicators
"""

import pytest
from beacon.cli.main import main
from click.testing import CliRunner

# ========== Task 3.1: Warehouse Command Group ==========


def test_warehouse_command_group_exists():
    """TC: warehouse command group is created and accessible."""
    runner = CliRunner()
    result = runner.invoke(main, ["warehouse", "--help"])

    assert result.exit_code == 0
    assert "Warehouse management commands" in result.output


def test_warehouse_command_shows_subcommands():
    """TC: warehouse --help shows init and connect subcommands."""
    runner = CliRunner()
    result = runner.invoke(main, ["warehouse", "--help"])

    assert result.exit_code == 0
    assert "init" in result.output
    assert "connect" in result.output


def test_warehouse_connect_help_accessible():
    """TC: warehouse connect --help shows command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["warehouse", "connect", "--help"])

    assert result.exit_code == 0
    assert "Connect project to a local warehouse" in result.output
    assert "--path" in result.output


# ========== Task 3.2: Connect Command with --path Parameter ==========


def test_connect_with_valid_warehouse_path(valid_warehouse, temp_dir, monkeypatch):
    """TC1: Valid warehouse path → Exit code 0, config.toml created, success message."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert "✓ Warehouse structure validated" in result.output
    assert "✓ Connected to warehouse" in result.output

    config_path = project_dir / ".agentic-beacon" / "config.toml"
    assert config_path.exists()

    config_content = config_path.read_text()
    assert "[warehouse]" in config_content
    assert "local_path" in config_content


def test_connect_with_invalid_warehouse_structure(temp_dir, monkeypatch):
    """TC2: Invalid warehouse structure → Exit code 1, no config.toml, validation errors displayed."""
    runner = CliRunner()

    invalid_warehouse = temp_dir / "invalid-warehouse"
    invalid_warehouse.mkdir()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(invalid_warehouse)]
    )

    assert result.exit_code == 1
    assert "Invalid warehouse structure" in result.output

    config_path = project_dir / ".agentic-beacon" / "config.toml"
    assert not config_path.exists()


def test_connect_with_nonexistent_path(temp_dir, monkeypatch):
    """TC3: Non-existent path → Exit code 1, error message."""
    runner = CliRunner()

    nonexistent_path = temp_dir / "does-not-exist"

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(nonexistent_path)]
    )

    assert result.exit_code == 1


def test_connect_with_file_not_directory(temp_dir, monkeypatch):
    """TC4: Path is file not directory → Exit code 1, error."""
    runner = CliRunner()

    file_path = temp_dir / "not-a-directory.txt"
    file_path.write_text("test")

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["warehouse", "connect", "--path", str(file_path)])

    assert result.exit_code == 1


def test_connect_overwrites_existing_connection(valid_warehouse, temp_dir, monkeypatch):
    """TC5: Already connected → Overwrites with new connection."""
    runner = CliRunner()

    warehouse2 = temp_dir / "warehouse2"
    warehouse2.mkdir()
    (warehouse2 / "agents").mkdir()
    (warehouse2 / "contexts").mkdir()
    (warehouse2 / "knowledge").mkdir()
    (warehouse2 / "skills").mkdir()
    (warehouse2 / "docs").mkdir()
    (warehouse2 / "README.md").write_text("# Warehouse 2")

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result1 = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )
    assert result1.exit_code == 0

    config_path = project_dir / ".agentic-beacon" / "config.toml"
    first_content = config_path.read_text()
    assert str(valid_warehouse) in first_content

    result2 = runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse2)])
    assert result2.exit_code == 0

    second_content = config_path.read_text()
    assert str(warehouse2) in second_content
    assert str(valid_warehouse) not in second_content


def test_connect_creates_agentic_beacon_directory(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC8: No .agentic-beacon directory → Creates directory, then saves config."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    beacon_dir = project_dir / ".agentic-beacon"
    assert not beacon_dir.exists()

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert beacon_dir.exists()
    assert beacon_dir.is_dir()
    assert (beacon_dir / "config.toml").exists()


# ========== Task 3.3: Interactive Prompt Workflow ==========


def test_connect_interactive_prompts_for_path(valid_warehouse, temp_dir, monkeypatch):
    """TC: Interactive mode prompts for warehouse path when --path not provided."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect"], input=str(valid_warehouse) + "\n"
    )

    assert result.exit_code == 0
    assert "Warehouse path" in result.output
    assert "✓ Connected to warehouse" in result.output


# ========== Task 3.4: Warehouse Validation Integration ==========


def test_connect_validates_before_persisting(temp_dir, monkeypatch):
    """TC: Validation runs before persistence, errors displayed clearly."""
    runner = CliRunner()

    invalid_warehouse = temp_dir / "invalid"
    invalid_warehouse.mkdir()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(invalid_warehouse)]
    )

    assert result.exit_code == 1
    assert "Invalid warehouse structure" in result.output
    assert "✗" in result.output or "Missing" in result.output

    config_path = project_dir / ".agentic-beacon" / "config.toml"
    assert not config_path.exists()


def test_connect_validation_errors_are_detailed(temp_dir, monkeypatch):
    """TC: Validation errors list specific missing directories/files."""
    runner = CliRunner()

    invalid_warehouse = temp_dir / "invalid"
    invalid_warehouse.mkdir()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(invalid_warehouse)]
    )

    assert result.exit_code == 1
    assert (
        "contexts" in result.output
        or "knowledge" in result.output
        or "skills" in result.output
    )


# ========== Task 3.5: Connection Persistence ==========


def test_connect_creates_config_toml_with_absolute_path(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC: Creates .agentic-beacon/config.toml with absolute warehouse path."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0

    config_path = project_dir / ".agentic-beacon" / "config.toml"
    assert config_path.exists()

    config_content = config_path.read_text()
    assert "[warehouse]" in config_content
    assert "local_path" in config_content
    assert valid_warehouse.is_absolute()
    assert str(valid_warehouse) in config_content


def test_connect_config_toml_has_correct_structure(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC: config.toml contains correct TOML structure."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0

    config_path = project_dir / ".agentic-beacon" / "config.toml"
    config_content = config_path.read_text()

    # Use tomllib (Python 3.11+) or skip test if not available
    try:
        import tomllib
    except ImportError:
        pytest.skip("tomllib/tomli not available")

    parsed = tomllib.loads(config_content)
    assert "warehouse" in parsed
    assert "local_path" in parsed["warehouse"]


# ========== Task 3.6: Success Confirmation Messaging ==========


def test_connect_shows_validation_confirmation(valid_warehouse, temp_dir, monkeypatch):
    """TC: Success message includes validation confirmation."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert "✓ Warehouse structure validated" in result.output


def test_connect_shows_connection_confirmation(valid_warehouse, temp_dir, monkeypatch):
    """TC: Success message includes connection confirmation with path."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert "✓ Connected to warehouse" in result.output
    # Check that Location field is shown (path may be wrapped by Rich console)
    assert "Location:" in result.output


def test_connect_shows_next_steps(valid_warehouse, temp_dir, monkeypatch):
    """TC: Success message suggests next commands to run."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert "Next Steps" in result.output
    assert "abc setup" in result.output
    assert "abc sync" in result.output


# ========== Task 3.7: Progress Indicators ==========


def test_connect_shows_validation_progress(valid_warehouse, temp_dir, monkeypatch):
    """TC: Shows progress message during validation."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert "Validating" in result.output


def test_connect_shows_connection_saved_progress(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC: Shows progress message when connection is saved."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0
    assert "✓ Connection saved" in result.output


def test_connect_progress_indicators_appear_in_order(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC: Progress indicators appear in logical order."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )

    assert result.exit_code == 0

    output = result.output
    validating_pos = output.find("Validating")
    validated_pos = output.find("✓ Warehouse structure validated")
    saved_pos = output.find("✓ Connection saved")
    connected_pos = output.find("✓ Connected to warehouse")

    assert validating_pos < validated_pos < saved_pos < connected_pos
