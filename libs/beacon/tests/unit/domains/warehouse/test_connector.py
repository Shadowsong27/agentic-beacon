"""Unit tests for connect_to_warehouse orchestration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from beacon.core.manifest.beacon import ValidationResult
from beacon.domains.warehouse.connector import ConnectResult, connect_to_warehouse


def _make_valid_result() -> ValidationResult:
    return ValidationResult(valid=True, errors=[])


def _make_invalid_result(errors: list[str]) -> ValidationResult:
    return ValidationResult(valid=False, errors=errors)


class TestConnectToWarehouseValidation:
    def test_returns_invalid_connect_result_when_warehouse_invalid(
        self, tmp_path: Path
    ) -> None:
        warehouse = tmp_path / "wh"
        project = tmp_path / "proj"
        project.mkdir()

        with patch("beacon.domains.warehouse.connector.WarehouseValidator") as mock_cls:
            mock_cls.return_value.validate.return_value = _make_invalid_result(
                ["missing agents/"]
            )
            result = connect_to_warehouse(project, warehouse)

        assert not result.valid
        assert "missing agents/" in result.errors

    def test_returns_invalid_result_without_touching_fs(self, tmp_path: Path) -> None:
        warehouse = tmp_path / "wh"
        project = tmp_path / "proj"
        project.mkdir()

        with patch("beacon.domains.warehouse.connector.WarehouseValidator") as mock_cls:
            mock_cls.return_value.validate.return_value = _make_invalid_result(["err"])
            connect_to_warehouse(project, warehouse)

        assert not (project / ".agentic-beacon").exists()


class TestConnectToWarehouseSuccess:
    @pytest.fixture()
    def project(self, tmp_path: Path) -> Path:
        p = tmp_path / "proj"
        p.mkdir()
        return p

    @pytest.fixture()
    def warehouse(self, tmp_path: Path) -> Path:
        w = tmp_path / "wh"
        w.mkdir()
        return w

    def test_creates_beacon_dir_under_project_root(
        self, project: Path, warehouse: Path
    ) -> None:
        with (
            patch(
                "beacon.domains.warehouse.connector.WarehouseValidator"
            ) as mock_validator_cls,
            patch(
                "beacon.domains.warehouse.connector.WorkspaceConfig.from_path"
            ) as mock_from_path,
            patch("beacon.domains.warehouse.connector.GitignoreManager") as mock_gi_cls,
        ):
            mock_validator_cls.return_value.validate.return_value = _make_valid_result()
            mock_from_path.return_value = MagicMock()
            mock_gi_cls.return_value.ensure_entries.return_value = True

            connect_to_warehouse(project, warehouse)

        assert (project / ".agentic-beacon").is_dir()

    def test_persists_config_with_project_root(
        self, project: Path, warehouse: Path
    ) -> None:
        with (
            patch(
                "beacon.domains.warehouse.connector.WarehouseValidator"
            ) as mock_validator_cls,
            patch(
                "beacon.domains.warehouse.connector.WorkspaceConfig.from_path"
            ) as mock_from_path,
            patch("beacon.domains.warehouse.connector.GitignoreManager") as mock_gi_cls,
        ):
            mock_validator_cls.return_value.validate.return_value = _make_valid_result()
            mock_from_path.return_value = MagicMock()
            mock_gi_cls.return_value.ensure_entries.return_value = False

            connect_to_warehouse(project, warehouse)

        mock_from_path.assert_called_once_with(warehouse, project_root=project)

    def test_updates_gitignore(self, project: Path, warehouse: Path) -> None:
        with (
            patch(
                "beacon.domains.warehouse.connector.WarehouseValidator"
            ) as mock_validator_cls,
            patch(
                "beacon.domains.warehouse.connector.WorkspaceConfig.from_path"
            ) as mock_from_path,
            patch("beacon.domains.warehouse.connector.GitignoreManager") as mock_gi_cls,
        ):
            mock_validator_cls.return_value.validate.return_value = _make_valid_result()
            mock_from_path.return_value = MagicMock()
            mock_gi_cls.return_value.ensure_entries.return_value = True

            result = connect_to_warehouse(project, warehouse)

        mock_gi_cls.assert_called_once_with(project)
        mock_gi_cls.return_value.ensure_entries.assert_called_once()
        assert result.gitignore_updated is True

    def test_returns_connect_result_shape(self, project: Path, warehouse: Path) -> None:
        with (
            patch(
                "beacon.domains.warehouse.connector.WarehouseValidator"
            ) as mock_validator_cls,
            patch(
                "beacon.domains.warehouse.connector.WorkspaceConfig.from_path"
            ) as mock_from_path,
            patch("beacon.domains.warehouse.connector.GitignoreManager") as mock_gi_cls,
        ):
            mock_validator_cls.return_value.validate.return_value = _make_valid_result()
            mock_from_path.return_value = MagicMock()
            mock_gi_cls.return_value.ensure_entries.return_value = False

            result = connect_to_warehouse(project, warehouse)

        assert isinstance(result, ConnectResult)
        assert result.valid is True
        assert result.errors == []
        assert result.gitignore_updated is False
