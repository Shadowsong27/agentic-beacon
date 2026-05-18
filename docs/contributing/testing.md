# Testing

Testing conventions and patterns for the Agentic Beacon project.

---

## Overview

Tests live under `libs/beacon/tests/` and are split into two suites:

| Suite | Location | Marker | Run command |
|---|---|---|---|
| Unit | `tests/unit/` | (none — default) | `pytest -m "not integration"` |
| Integration | `tests/integration/` | `@pytest.mark.integration` | `pytest -m integration` |

Run from the **repo root**, not from `libs/beacon/`:

```bash
pytest                              # all tests
pytest -m "not integration"         # unit tests only (fast)
pytest -m integration               # integration tests only
pytest -x                           # stop at first failure
pytest -k "test_name_fragment"      # filter by name
pytest tests/unit/domains/adoption/ # specific directory
```

---

## Unit Test Layout

```
tests/unit/
├── test_architecture.py          # layering rule enforcement (AST-based)
├── test_adopt.py
├── test_wire_agents.py
├── test_pending.py
├── core/
│   ├── test_sync_engine_symlinks.py
│   ├── test_orchestrator.py
│   ├── test_delta_comparator.py
│   ├── test_beacon_yaml_parser.py
│   ├── dependencies/
│   │   ├── test_resolver.py
│   │   ├── test_agent_manifest.py
│   │   └── test_frontmatter.py
│   └── manifest/
│       ├── test_beacon.py
│       └── test_manifest_changes.py
└── domains/
    ├── adoption/
    │   ├── test_apply_commit.py    # atomic commit + rollback
    │   ├── test_tui_pending.py
    │   ├── test_tui_agents.py
    │   └── test_tui_agents_state_machine.py
    ├── warehouse/
    │   ├── test_validator.py
    │   └── test_connector.py
    └── distribution/
        └── test_artifact_listing.py
```

---

## Fixtures and Isolation

### `tmp_path` for filesystem isolation

Always use pytest's built-in `tmp_path` fixture. Never use `tempfile.mkdtemp()`:

```python
def test_something(tmp_path: Path) -> None:
    wh = tmp_path / "warehouse"
    wh.mkdir()
    ...
```

### Composed fixtures

Build specialized fixtures on top of `tmp_path`:

```python
@pytest.fixture
def fake_warehouse(tmp_path: Path) -> Path:
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / ".git").mkdir()
    (wh / "skills" / "example").mkdir(parents=True)
    (wh / "skills" / "example" / "SKILL.md").write_text("# Example skill\n")
    return wh

@pytest.fixture
def engine(fake_warehouse: Path, tmp_path: Path) -> SyncEngine:
    artifacts = tmp_path / "project" / ".agentic-beacon" / "artifacts"
    artifacts.mkdir(parents=True)
    return SyncEngine(warehouse_path=fake_warehouse, artifacts_path=artifacts)
```

### Test classes for grouping

Group related tests in a class when they share a meaningful concern boundary:

```python
class TestSymlinkCreation:
    def test_creates_symlink(self, engine: SyncEngine, ...) -> None: ...
    def test_idempotent_ok(self, engine: SyncEngine, ...) -> None: ...

class TestOutOfWarehouseGuard:
    def test_raises_on_path_escape(self, engine: SyncEngine, ...) -> None: ...
```

Top-level functions are also fine when tests do not share state.

---

## Dependency Injection Instead of Mocking

Prefer injectable callables over `unittest.mock.patch` for side-effect isolation.

Domain functions that touch the filesystem accept optional `_callable` parameters:

```python
def commit_session(
    ...,
    _symlink_sync_fn: Callable = _default_sync,
    _post_sync_wiring_fn: Callable = _default_post_sync_wiring,
) -> list[str]:
```

Test by injecting no-ops or failure simulators:

```python
def _noop_sync(*args, **kwargs) -> None:
    return

def _failing_sync(*args, **kwargs) -> None:
    raise RuntimeError("simulated sync failure")

# Test normal path
commit_session(..., _symlink_sync_fn=_noop_sync, _post_sync_wiring_fn=_noop_sync)

# Test rollback path
with pytest.raises(CommitError):
    commit_session(..., _symlink_sync_fn=_failing_sync)
```

Reserve `unittest.mock.patch` for cases where the callable injection pattern is not available
(e.g., `test_connector.py` patches `WarehouseValidator` at import time).

---

## Rollback Testing

Capture pre-state as raw bytes before the failing operation, then assert byte equality after:

```python
pre_beacon = beacon_yaml.read_bytes()
pre_pending = pending_yaml.read_bytes()

with pytest.raises(CommitError):
    commit_session(..., _symlink_sync_fn=_failing_sync, ...)

# Both files must be exactly restored
assert beacon_yaml.read_bytes() == pre_beacon
assert pending_yaml.read_bytes() == pre_pending
```

---

## Real Git in Unit Tests

Some unit tests initialize real git repositories in `tmp_path`. Always configure git identity
per-repo to avoid failures on machines without a global git config:

```python
def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)

def _git_commit(path: Path, msg: str) -> None:
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=path, check=True, capture_output=True)
```

---

## Architecture Tests

`test_architecture.py` enforces layering rules using Python's `ast` module. It walks source
files without importing them — a compile-time enforcement that catches violations at test time.

**What is enforced:**

| TC | Rule |
|---|---|
| TC1 | Exactly 5 domain directories exist |
| TC2 | No stray top-level modules in `beacon/` |
| TC3 | `core/` has no domain imports |
| TC4 | `utils/` has no higher-layer imports |
| TC5 | Cross-domain imports use depth ≤ 4 |
| TC6 | No underscore cross-module imports |
| TC7 | All `__init__.py` files are empty markers |
| TC8 | CLI handlers perform no I/O |
| TC9/9b | CLI handlers have at most one domain call |
| TC10 | Domains and core do not import `click`, `rich`, or call `sys.exit()` |

**Known waivers** are tracked in `_TC9B_WAIVERS` and `_TC10_WAIVERS`. Waivers that become
stale (the referenced file or handler no longer exists) cause test failures automatically.

**Adding a new architecture rule:** Add a new test function with the next `TC` number, use
`ast.parse()` + `ast.walk()`, and add a comment explaining what is being enforced and why.

---

## Integration Tests

Integration tests run against real in-memory git repos and real symlinks. They are marked
`@pytest.mark.integration` and run in a separate pytest pass in CI.

All integration tests use:

- **`e2e_warehouse`** fixture — creates a real git repo via subprocess in `tmp_path`
- **`e2e_project`** fixture — composes `tmp_path`, `e2e_warehouse`, and `monkeypatch.chdir()`
- **`isolated_home`** fixture — prevents touching real `~/.config/opencode/` or `~/.claude/`
- **`CliRunner`** from Click — invokes `main` (the CLI group) and captures stdout/stderr

```python
@pytest.mark.integration
def test_sync_creates_symlinks(e2e_project: Path, e2e_warehouse: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0
    assert (e2e_project / ".agentic-beacon" / "artifacts" / "skills" / "example" / "SKILL.md").is_symlink()
```

---

## Test Naming Conventions

| Pattern | Example |
|---|---|
| Action under test | `test_creates_symlink_in_artifacts_dir` |
| Condition-based | `test_raises_when_warehouse_not_connected` |
| Rollback/negative | `test_rollback_restores_beacon_yaml_on_sync_failure` |
| Architecture tests | `test_core_has_no_domain_imports` |

Use `pytest.raises` with `match=` parameter to assert specific error messages:

```python
with pytest.raises(ConfigurationError, match="must be an absolute path"):
    WorkspaceConfig(warehouse=WarehouseConfig(local_path=Path("relative")))
```

---

## Coverage

```bash
pytest -m "not integration" --cov=beacon --cov-report=term-missing
pytest -m integration --cov=beacon --cov-report=term-missing --cov-append
```

There is no enforced coverage gate in CI. Coverage reports are informational.
