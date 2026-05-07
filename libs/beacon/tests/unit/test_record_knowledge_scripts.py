"""Unit tests for resolve_warehouse.py and append_pending.py helper scripts.

Parametrised over both record-knowledge and record-skill to verify that
both independent copies satisfy the same contract (design.md Decision 7:
duplication over coupling).

Tests match the TDD criteria in tasks.md sections 7.1, 7.2, 8.1, 8.2.
"""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

_SKILLS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "beacon" / "data" / "skills"
)


def _load_script(skill_name: str, script_name: str):
    """Load a PEP 723 script file as an importlib module."""
    script_path = _SKILLS_DIR / skill_name / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(
        f"{skill_name.replace('-', '_')}_{script_name.replace('.py', '')}",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Parametrised fixtures — each test class runs once per skill
# ---------------------------------------------------------------------------


@pytest.fixture(params=["record-knowledge", "record-skill"])
def resolve_mod(request):
    """resolve_warehouse.py module for the parametrised skill."""
    return _load_script(request.param, "resolve_warehouse.py")


@pytest.fixture(params=["record-knowledge", "record-skill"])
def append_mod(request):
    """append_pending.py module for the parametrised skill."""
    return _load_script(request.param, "append_pending.py")


# ---------------------------------------------------------------------------
# resolve_warehouse.py — find_project_root()
# ---------------------------------------------------------------------------


class TestFindProjectRoot:
    def test_finds_root_at_start_dir(self, resolve_mod, tmp_path):
        """TC1: config.toml at start → returns start."""
        (tmp_path / ".agentic-beacon").mkdir()
        (tmp_path / ".agentic-beacon" / "config.toml").write_text(
            '[warehouse]\nlocal_path = "/tmp/wh"\n'
        )
        assert resolve_mod.find_project_root(tmp_path) == tmp_path.resolve()

    def test_walks_up_from_nested_subdir(self, resolve_mod, tmp_path):
        """TC2: config.toml at ancestor → walks up and finds it."""
        (tmp_path / ".agentic-beacon").mkdir()
        (tmp_path / ".agentic-beacon" / "config.toml").write_text(
            '[warehouse]\nlocal_path = "/tmp/wh"\n'
        )
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert resolve_mod.find_project_root(nested) == tmp_path.resolve()

    def test_returns_none_when_no_config_in_tree(self, resolve_mod, tmp_path):
        """TC3: no config.toml in any ancestor → returns None."""
        assert resolve_mod.find_project_root(tmp_path) is None


# ---------------------------------------------------------------------------
# resolve_warehouse.py — get_warehouse_path()
# ---------------------------------------------------------------------------


class TestGetWarehousePath:
    def _make_config(self, project_root: Path, warehouse_path: str) -> None:
        beacon_dir = project_root / ".agentic-beacon"
        beacon_dir.mkdir(parents=True, exist_ok=True)
        (beacon_dir / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{warehouse_path}"\n'
        )

    def test_returns_absolute_warehouse_path(self, resolve_mod, tmp_path):
        """TC1: valid config.toml → returns absolute warehouse path string."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        self._make_config(tmp_path, str(warehouse))
        result = resolve_mod.get_warehouse_path(tmp_path)
        assert result == str(warehouse.resolve())

    def test_walks_up_from_nested_subdir(self, resolve_mod, tmp_path):
        """TC2: nested subdir → walks up to find config."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        self._make_config(tmp_path, str(warehouse))
        nested = tmp_path / "x" / "y"
        nested.mkdir(parents=True)
        result = resolve_mod.get_warehouse_path(nested)
        assert result == str(warehouse.resolve())

    def test_no_config_exits_nonzero_with_documented_error(
        self, resolve_mod, tmp_path, capsys
    ):
        """TC3: no config.toml → SystemExit(1) with documented error text on stderr."""
        with pytest.raises(SystemExit) as exc:
            resolve_mod.get_warehouse_path(tmp_path)
        assert exc.value.code == 1
        assert "Error: no warehouse connected" in capsys.readouterr().err

    def test_missing_warehouse_section_exits_nonzero(
        self, resolve_mod, tmp_path, capsys
    ):
        """TC4: config.toml missing [warehouse] section → SystemExit(1)."""
        beacon_dir = tmp_path / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text("[other]\nkey = 1\n")
        with pytest.raises(SystemExit) as exc:
            resolve_mod.get_warehouse_path(tmp_path)
        assert exc.value.code == 1
        assert "warehouse" in capsys.readouterr().err.lower()

    def test_missing_local_path_exits_nonzero(self, resolve_mod, tmp_path, capsys):
        """TC5: [warehouse] present but no local_path → SystemExit(1)."""
        beacon_dir = tmp_path / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text("[warehouse]\nother_key = 1\n")
        with pytest.raises(SystemExit) as exc:
            resolve_mod.get_warehouse_path(tmp_path)
        assert exc.value.code == 1
        assert "local_path" in capsys.readouterr().err

    def test_pep723_metadata_block_present(self, resolve_mod):
        """TC6: script file has a valid PEP 723 # /// script ... # /// header."""
        source = Path(resolve_mod.__file__).read_text()
        assert "# /// script" in source
        assert "requires-python" in source
        assert "# ///" in source


# ---------------------------------------------------------------------------
# append_pending.py — find_project_root() (same contract as resolve's)
# ---------------------------------------------------------------------------


class TestAppendFindProjectRoot:
    def test_finds_root_at_start_dir(self, append_mod, tmp_path):
        """TC1: config.toml at start → returns start."""
        (tmp_path / ".agentic-beacon").mkdir()
        (tmp_path / ".agentic-beacon" / "config.toml").write_text(
            '[warehouse]\nlocal_path = "/tmp/wh"\n'
        )
        assert append_mod.find_project_root(tmp_path) == tmp_path.resolve()

    def test_returns_none_when_no_config_in_tree(self, append_mod, tmp_path):
        """TC5: no config.toml → returns None."""
        assert append_mod.find_project_root(tmp_path) is None


# ---------------------------------------------------------------------------
# append_pending.py — append_pending_entry()
# ---------------------------------------------------------------------------


class TestAppendPendingEntry:
    def _make_project(self, tmp_path: Path) -> Path:
        beacon_dir = tmp_path / ".agentic-beacon"
        beacon_dir.mkdir(parents=True)
        (beacon_dir / "config.toml").write_text(
            f'[warehouse]\nlocal_path = "{tmp_path}"\n'
        )
        return tmp_path

    def test_creates_pending_yaml_when_absent(self, append_mod, tmp_path):
        """TC1: pending.yaml absent → created with single entry."""
        project_root = self._make_project(tmp_path)
        append_mod.append_pending_entry(
            project_root,
            path="knowledge/lessons/x.md",
            type_="knowledge",
            action="created",
            source="record-knowledge",
        )
        pending_path = project_root / ".agentic-beacon" / "pending.yaml"
        assert pending_path.exists()
        from beacon.core.manifest.pending import PendingManifest

        manifest = PendingManifest.from_yaml(pending_path)
        assert len(manifest.pending) == 1
        assert manifest.pending[0].path == "knowledge/lessons/x.md"

    def test_appends_on_second_call_preserving_order(self, append_mod, tmp_path):
        """TC2: second call → length 2, insertion order preserved."""
        project_root = self._make_project(tmp_path)
        append_mod.append_pending_entry(
            project_root,
            path="knowledge/lessons/first.md",
            type_="knowledge",
            action="created",
            source="s",
        )
        append_mod.append_pending_entry(
            project_root,
            path="knowledge/lessons/second.md",
            type_="knowledge",
            action="modified",
            source="s",
        )
        from beacon.core.manifest.pending import PendingManifest

        manifest = PendingManifest.from_yaml(
            project_root / ".agentic-beacon" / "pending.yaml"
        )
        assert len(manifest.pending) == 2
        assert manifest.pending[0].path == "knowledge/lessons/first.md"
        assert manifest.pending[1].path == "knowledge/lessons/second.md"

    def test_source_accepts_free_form_string(self, append_mod, tmp_path):
        """TC6: source accepts any free-form string, no enum check."""
        project_root = self._make_project(tmp_path)
        append_mod.append_pending_entry(
            project_root,
            path="skills/x/",
            type_="skill",
            action="created",
            source="my-custom-authoring-tool-v2",
        )
        from beacon.core.manifest.pending import PendingManifest

        manifest = PendingManifest.from_yaml(
            project_root / ".agentic-beacon" / "pending.yaml"
        )
        assert manifest.pending[0].source == "my-custom-authoring-tool-v2"

    def test_created_at_is_utc_aware(self, append_mod, tmp_path):
        """TC7: created_at field is timezone-aware UTC, not naive."""
        project_root = self._make_project(tmp_path)
        before = datetime.now(UTC)
        append_mod.append_pending_entry(
            project_root,
            path="knowledge/facts/x.md",
            type_="knowledge",
            action="created",
            source="test",
        )
        after = datetime.now(UTC)
        from beacon.core.manifest.pending import PendingManifest

        manifest = PendingManifest.from_yaml(
            project_root / ".agentic-beacon" / "pending.yaml"
        )
        entry_dt = manifest.pending[0].created_at
        assert entry_dt.tzinfo is not None
        # to_yaml truncates to second precision; compare against truncated before
        assert before.replace(microsecond=0) <= entry_dt <= after

    def test_pep723_metadata_block_present(self, append_mod):
        """PEP 723 header present in append_pending.py."""
        source = Path(append_mod.__file__).read_text()
        assert "# /// script" in source
        assert "requires-python" in source


# ---------------------------------------------------------------------------
# append_pending.py — main() argument validation
# ---------------------------------------------------------------------------


class TestAppendMainArgValidation:
    def test_missing_path_exits_nonzero(self, append_mod, monkeypatch):
        """TC3: missing --path → argparse exits non-zero."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "append_pending.py",
                "--type",
                "knowledge",
                "--action",
                "created",
                "--source",
                "test",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            append_mod.main()
        assert exc.value.code != 0

    def test_invalid_type_exits_nonzero(self, append_mod, monkeypatch, capsys):
        """TC4: invalid --type value → argparse exits non-zero."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "append_pending.py",
                "--path",
                "x.md",
                "--type",
                "invalid-type",
                "--action",
                "created",
                "--source",
                "test",
            ],
        )
        with pytest.raises(SystemExit) as exc:
            append_mod.main()
        assert exc.value.code != 0

    def test_no_config_in_cwd_exits_nonzero(
        self, append_mod, monkeypatch, capsys, tmp_path
    ):
        """TC5: outside any project → SystemExit(1) with documented error text."""
        monkeypatch.setattr(
            "sys.argv",
            [
                "append_pending.py",
                "--path",
                "x.md",
                "--type",
                "knowledge",
                "--action",
                "created",
                "--source",
                "test",
            ],
        )
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            append_mod.main()
        assert exc.value.code == 1
        assert "Error: no warehouse connected" in capsys.readouterr().err
