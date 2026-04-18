"""Tests for global agent sync-state helpers.

TDD Test Cases for _read_global_sync_state / _write_global_sync_state (4.1):
- TC1: File does not exist → returns {}
- TC2: File exists with valid JSON including version field → returns parsed dict
- TC3: _write_global_sync_state() with new data → file created with "version": 1
- TC4: _write_global_sync_state() overwrites existing → file updated, version preserved
- TC5: File exists with unknown version value → reader warns and returns {}
- TC6: File exists with invalid JSON → reader warns and returns {}

TDD Test Cases for _relink_global_sync_state (4.3):
- TC1: No state file → no prompt, returns False
- TC2: State file has entry for current path → no prompt, returns False
- TC3: State file has entry for /old/path/warehouse, current path is /new/path/warehouse → prompt shown
- TC4: User confirms relink → key renamed in state file, returns True
- TC5: User declines → state file unchanged, returns False
- TC6: Multiple old paths with same dir name → prompt shows all candidates
"""

import json

from beacon.utils.sync_state import (
    _read_global_sync_state,
    _relink_global_sync_state,
    _write_global_sync_state,
)


class TestReadWriteGlobalSyncState:
    """Tests for _read_global_sync_state / _write_global_sync_state covering TC1-TC6."""

    def test_tc1_file_does_not_exist(self, tmp_path, monkeypatch):
        """TC1: File does not exist → returns {}."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = _read_global_sync_state()
        assert result == {}

    def test_tc2_valid_json_with_version(self, tmp_path, monkeypatch):
        """TC2: File exists with valid JSON including version field → returns parsed dict."""
        fake_home = tmp_path / "home"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        data = {"version": 1, "warehouses": {"/some/path": {}}}
        state_file.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = _read_global_sync_state()
        assert result["version"] == 1
        assert "warehouses" in result

    def test_tc3_write_creates_file_with_version(self, tmp_path, monkeypatch):
        """TC3: _write_global_sync_state() with new data → file created with "version": 1."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        _write_global_sync_state({"warehouses": {}})

        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["version"] == 1

    def test_tc4_write_overwrites_existing(self, tmp_path, monkeypatch):
        """TC4: _write_global_sync_state() overwrites existing → updated, version preserved."""
        fake_home = tmp_path / "home"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(json.dumps({"version": 1, "warehouses": {}}))
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        _write_global_sync_state({"warehouses": {"/new/path": {"file.md": {}}}})

        data = json.loads(state_file.read_text())
        assert data["version"] == 1
        assert "/new/path" in data["warehouses"]

    def test_tc5_unknown_version_returns_empty(self, tmp_path, monkeypatch):
        """TC5: File exists with unknown version value → warns and returns {}."""
        fake_home = tmp_path / "home"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(json.dumps({"version": 99, "warehouses": {}}))
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = _read_global_sync_state()
        assert result == {}

    def test_tc6_invalid_json_returns_empty(self, tmp_path, monkeypatch):
        """TC6: File exists with invalid JSON → warns and returns {}."""
        fake_home = tmp_path / "home"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text("not valid json {{{{")
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = _read_global_sync_state()
        assert result == {}


class TestRelinkGlobalSyncState:
    """Tests for _relink_global_sync_state covering TC1-TC6."""

    def test_tc1_no_state_file_returns_false(self, tmp_path, monkeypatch):
        """TC1: No state file → no prompt, returns False."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = _relink_global_sync_state(tmp_path / "my-warehouse")
        assert result is False

    def test_tc2_state_has_current_path_returns_false(self, tmp_path, monkeypatch):
        """TC2: State file has entry for current path → no prompt, returns False."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        warehouse = tmp_path / "my-warehouse"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps({"version": 1, "warehouses": {str(warehouse): {}}})
        )
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = _relink_global_sync_state(warehouse)
        assert result is False

    def test_tc3_matching_dir_name_prompts(self, tmp_path, monkeypatch):
        """TC3: State has entry for /old/path/warehouse, current is /new/path/warehouse → prompt."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        old_path = "/old/path/my-warehouse"
        new_warehouse = tmp_path / "my-warehouse"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps({"version": 1, "warehouses": {old_path: {"file.md": {}}}})
        )
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        # Simulate user answering "N" (decline)
        monkeypatch.setattr("click.prompt", lambda *a, **kw: "N")
        result = _relink_global_sync_state(new_warehouse)
        assert result is False

    def test_tc4_user_confirms_relinks(self, tmp_path, monkeypatch):
        """TC4: User confirms relink → key renamed in state file, returns True."""
        import json as _json

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        old_path = "/old/path/my-warehouse"
        new_warehouse = tmp_path / "my-warehouse"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps({"version": 1, "warehouses": {old_path: {"file.md": {}}}})
        )
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
        monkeypatch.setattr("click.prompt", lambda *a, **kw: "y")

        result = _relink_global_sync_state(new_warehouse)
        assert result is True

        data = _json.loads(state_file.read_text())
        assert str(new_warehouse) in data["warehouses"]
        assert old_path not in data["warehouses"]

    def test_tc5_user_declines_no_change(self, tmp_path, monkeypatch):
        """TC5: User declines → state file unchanged, returns False."""
        import json as _json

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        old_path = "/old/path/my-warehouse"
        new_warehouse = tmp_path / "my-warehouse"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        original_data = {"version": 1, "warehouses": {old_path: {"file.md": {}}}}
        state_file.write_text(json.dumps(original_data))
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
        monkeypatch.setattr("click.prompt", lambda *a, **kw: "N")

        result = _relink_global_sync_state(new_warehouse)
        assert result is False

        data = _json.loads(state_file.read_text())
        assert old_path in data["warehouses"]

    def test_tc6_multiple_candidates_shows_all(self, tmp_path, monkeypatch):
        """TC6: Multiple old paths with same dir name → prompt shows options, user picks."""

        fake_home = tmp_path / "home"
        fake_home.mkdir()
        old_path1 = "/old/path1/my-warehouse"
        old_path2 = "/old/path2/my-warehouse"
        new_warehouse = tmp_path / "my-warehouse"
        state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
        state_file.parent.mkdir(parents=True)
        state_file.write_text(
            json.dumps(
                {
                    "version": 1,
                    "warehouses": {
                        old_path1: {"a.md": {}},
                        old_path2: {"b.md": {}},
                    },
                }
            )
        )
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        # User selects option 1
        prompt_calls = []

        def mock_prompt(*a, **kw):
            prompt_calls.append(a)
            return "1"

        monkeypatch.setattr("click.prompt", mock_prompt)

        result = _relink_global_sync_state(new_warehouse)
        assert result is True
        assert len(prompt_calls) > 0
