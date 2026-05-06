"""Unit tests for warehouse path validation."""

from beacon.domains.warehouse.warehouse_path import (
    WarehousePathMissing,
    WarehousePathNotARepo,
    WarehousePathOK,
    validate_warehouse_path,
)


class TestValidateWarehousePath:
    """Test cases for validate_warehouse_path (task 1.2 TCs)."""

    def test_existing_git_dir_returns_ok(self, tmp_path):
        """TC1: Path exists and contains a .git/ directory -> returns OK variant."""
        git_dir = tmp_path / "warehouse"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()
        result = validate_warehouse_path(git_dir)
        assert isinstance(result, WarehousePathOK)
        assert result.path == git_dir.resolve()

    def test_nested_subdir_returns_git_root(self, tmp_path):
        """TC2: Path exists and is inside a git working tree -> returns OK pointing at git root."""
        git_root = tmp_path / "warehouse"
        git_root.mkdir()
        (git_root / ".git").mkdir()
        nested = git_root / "sub" / "dir"
        nested.mkdir(parents=True)
        result = validate_warehouse_path(nested)
        assert isinstance(result, WarehousePathOK)
        assert result.path == git_root.resolve()

    def test_nonexistent_returns_missing(self, tmp_path):
        """TC3: Path does not exist -> returns Missing variant."""
        missing = tmp_path / "does-not-exist"
        result = validate_warehouse_path(missing)
        assert isinstance(result, WarehousePathMissing)
        assert result.path == missing.resolve()

    def test_regular_file_returns_not_a_repo(self, tmp_path):
        """TC4: Path exists but is a regular file -> returns NotARepo variant."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("hello")
        result = validate_warehouse_path(file_path)
        assert isinstance(result, WarehousePathNotARepo)
        assert "regular file" in result.reason

    def test_no_git_anywhere_returns_not_a_repo(self, tmp_path):
        """TC5: Path exists but has no .git/ anywhere up the tree -> returns NotARepo."""
        plain_dir = tmp_path / "plain"
        plain_dir.mkdir()
        result = validate_warehouse_path(plain_dir)
        assert isinstance(result, WarehousePathNotARepo)
        assert ".git" in result.reason

    def test_relative_path_normalized_to_absolute(self, tmp_path, monkeypatch):
        """TC6: Relative path input -> validator normalizes to absolute before returning."""
        git_dir = tmp_path / "warehouse"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        result = validate_warehouse_path("warehouse")
        assert isinstance(result, WarehousePathOK)
        assert result.path.is_absolute()
        assert result.path == git_dir.resolve()

    def test_symlink_to_git_worktree_returns_resolved_path(self, tmp_path):
        """TC7: Path is a symlink to a valid git worktree -> returns OK with resolved absolute path."""
        git_dir = tmp_path / "real-warehouse"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()
        symlink = tmp_path / "link"
        symlink.symlink_to(git_dir)
        result = validate_warehouse_path(symlink)
        assert isinstance(result, WarehousePathOK)
        assert result.path == git_dir.resolve()
        # The result path should be the resolved real path, not the symlink path
        assert result.path == symlink.resolve()
