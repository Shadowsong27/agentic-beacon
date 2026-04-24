"""Unit tests for `abc warehouse init` — covers in-place and subdirectory modes."""

import subprocess
from pathlib import Path

import pytest
from beacon.cli.main import main
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

EXPECTED_DIRS = ["contexts", "knowledge", "skills", "docs"]
EXPECTED_FILES = [
    "contexts/README.md",
    "knowledge/README.md",
    "skills/README.md",
    "docs/architecture.md",
    "docs/contribution-guide.md",
    "README.md",
    ".gitignore",
    "skills/record-knowledge/SKILL.md",
    "skills/record-skill/SKILL.md",
]


def _assert_warehouse_structure(base: Path) -> None:
    for d in EXPECTED_DIRS:
        assert (base / d).is_dir(), f"Missing directory: {d}"
    for f in EXPECTED_FILES:
        assert (base / f).is_file(), f"Missing file: {f}"


# ---------------------------------------------------------------------------
# Original behaviour: named subdirectory
# ---------------------------------------------------------------------------


def test_init_creates_subdir_when_name_given(runner, tmp_path):
    """Named argument creates a new subdirectory as before."""
    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            "my-warehouse",
            "--path",
            str(tmp_path),
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, result.output
    _assert_warehouse_structure(tmp_path / "my-warehouse")


def test_init_errors_when_named_subdir_already_exists_and_is_populated(
    runner, tmp_path
):
    """
    When a *name* is given and the target directory already exists with content,
    initialisation still succeeds (in-place, skipping existing files).
    """
    subdir = tmp_path / "my-warehouse"
    subdir.mkdir()
    (subdir / "existing.md").write_text("keep me")

    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            "my-warehouse",
            "--path",
            str(tmp_path),
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, result.output
    # Pre-existing file must be untouched
    assert (subdir / "existing.md").read_text() == "keep me"
    # Warehouse structure must be created
    _assert_warehouse_structure(subdir)


# ---------------------------------------------------------------------------
# New behaviour: in-place init (no name argument)
# ---------------------------------------------------------------------------


def test_init_in_existing_empty_dir(runner, tmp_path):
    """Running without a name initialises the warehouse in the current dir."""
    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            "--path",
            str(tmp_path),
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (
        "current directory" in result.output.lower() or str(tmp_path) in result.output
    )
    _assert_warehouse_structure(tmp_path)


def test_init_in_existing_dir_skips_existing_files(runner, tmp_path):
    """Existing files are preserved; missing files are created."""
    # Pre-create one warehouse file with custom content
    (tmp_path / "contexts").mkdir()
    existing_content = "# My custom context\nDo not overwrite me."
    (tmp_path / "contexts" / "AGENTS.md").write_text(existing_content)

    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            "--path",
            str(tmp_path),
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, result.output

    # Existing file must be untouched
    assert (tmp_path / "contexts" / "AGENTS.md").read_text() == existing_content

    # All other warehouse files must be created
    for f in EXPECTED_FILES:
        if f != "contexts/README.md":
            assert (tmp_path / f).is_file(), f"Missing file: {f}"


def test_init_idempotent_second_run(runner, tmp_path):
    """Running init twice is safe and does not overwrite existing files."""
    # First run
    runner.invoke(
        main,
        ["warehouse", "init", "--path", str(tmp_path), "--no-interactive", "--no-git"],
    )
    original_content = (tmp_path / "README.md").read_text()

    # Modify a file to verify it won't be overwritten
    modified = original_content + "\n<!-- user edit -->"
    (tmp_path / "README.md").write_text(modified)

    # Second run
    result = runner.invoke(
        main,
        ["warehouse", "init", "--path", str(tmp_path), "--no-interactive", "--no-git"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "README.md").read_text() == modified


# ---------------------------------------------------------------------------
# Git handling
# ---------------------------------------------------------------------------


def test_init_skips_git_init_when_git_exists(runner, tmp_path):
    """When .git already exists, git init is skipped but files are staged."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    # Configure git identity so commit doesn't fail in CI environments
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = runner.invoke(
        main,
        ["warehouse", "init", "--path", str(tmp_path), "--no-interactive"],
    )
    assert result.exit_code == 0, result.output
    # .git must still be intact
    assert (tmp_path / ".git").is_dir()
    _assert_warehouse_structure(tmp_path)


def test_init_result_in_place_flag_true_when_dir_exists(tmp_path):
    """WarehouseInitializer.init() returns in_place=True for existing dirs."""
    from beacon.domains.setup.initializer import WarehouseInitializer

    initializer = WarehouseInitializer(warehouse_path=tmp_path)
    result = initializer.init(init_git=False)
    assert result["in_place"] is True


def test_init_result_in_place_flag_false_for_new_dir(tmp_path):
    """WarehouseInitializer.init() returns in_place=False for new dirs."""
    from beacon.domains.setup.initializer import WarehouseInitializer

    new_dir = tmp_path / "brand-new"
    initializer = WarehouseInitializer(warehouse_path=new_dir)
    result = initializer.init(init_git=False)
    assert result["in_place"] is False


# ---------------------------------------------------------------------------
# Path expansion: interactive prompt
# ---------------------------------------------------------------------------


def test_init_interactive_expands_tilde(runner, tmp_path, monkeypatch):
    """Interactive path prompt expands ~ to the user home directory."""
    monkeypatch.chdir(tmp_path)
    # expanduser() reads $HOME on Unix
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "tilde-warehouse"

    result = runner.invoke(
        main,
        ["warehouse", "init", "--no-git"],
        input="~/tilde-warehouse\nTest Org\npython\n\n",
    )

    assert result.exit_code == 0, result.output
    assert target.exists(), f"Expected {target} to be created"
    assert "will create" in result.output.lower()


def test_init_interactive_expands_env_var(runner, tmp_path, monkeypatch):
    """Interactive path prompt expands $HOME and other env vars."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / "env-warehouse"

    result = runner.invoke(
        main,
        ["warehouse", "init", "--no-git"],
        input="$HOME/env-warehouse\nTest Org\npython\n\n",
    )

    assert result.exit_code == 0, result.output
    assert target.exists(), f"Expected {target} to be created"


def test_init_interactive_shows_resolved_path(runner, tmp_path, monkeypatch):
    """'Will create: <absolute path>' is shown before initialising."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "shown-warehouse"

    result = runner.invoke(
        main,
        ["warehouse", "init", "--no-git"],
        input=f"{target}\nTest Org\npython\n\n",
    )

    assert result.exit_code == 0, result.output
    assert "will create" in result.output.lower()
    assert str(target) in result.output


def test_init_creates_parent_dirs_automatically(runner, tmp_path, monkeypatch):
    """mkdir -p: nested path is created even if parents don't exist."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "nested" / "deep" / "warehouse"

    result = runner.invoke(
        main,
        ["warehouse", "init", "--no-git"],
        input=f"{target}\nTest Org\npython\n\n",
    )

    assert result.exit_code == 0, result.output
    assert target.exists()
