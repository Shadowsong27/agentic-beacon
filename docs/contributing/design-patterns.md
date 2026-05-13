# Design Patterns

Recurring patterns used throughout the Agentic Beacon codebase.

---

## Injectable Callables (Dependency Injection for Testability)

Domain functions that perform side effects accept optional callable parameters with `_` prefix
names. In production, the defaults are the real implementations. In tests, inject no-ops or
failure simulators:

```python
def commit_session(
    ...,
    _symlink_sync_fn: Callable = _default_sync,
    _post_sync_wiring_fn: Callable = _default_post_sync_wiring,
    _unlink_fn: Callable = Path.unlink,
) -> list[str]:
    ...
```

Test usage:

```python
def _noop_sync(*args, **kwargs) -> None:
    return

def _failing_sync(*args, **kwargs) -> None:
    raise RuntimeError("simulated sync error")

commit_session(..., _symlink_sync_fn=_noop_sync, _post_sync_wiring_fn=_noop_post_sync)
```

This avoids `unittest.mock.patch` and keeps test setup explicit and legible.

---

## Atomic Commit with Snapshot Rollback

When a sequence of filesystem writes must be atomic, capture pre-state before writing and
restore on any exception.

**Pattern used in `adoption/apply.py::commit_session()`:**

1. **Snapshot:** Read files as raw bytes before any mutation.
   ```python
   pre_beacon = beacon_yaml.read_bytes()
   pre_pending = pending_yaml.read_bytes()
   ```

2. **Accumulators:** Track every created path and every removed symlink.
   ```python
   created_paths: list[Path] = []
   removed_paths_with_target: list[tuple[Path, Path]] = []
   tool_snapshots: list[tuple[Path, str, Path | None]] = []
   ```

3. **Rollback:** On any exception, restore bytes and reverse filesystem mutations.
   ```python
   def _rollback() -> None:
       beacon_yaml.write_bytes(pre_beacon)
       pending_yaml.write_bytes(pre_pending)
       for path in created_paths:
           path.unlink(missing_ok=True)
       for path, target in removed_paths_with_target:
           path.symlink_to(target)
       ...
   ```

4. **Deferred imports:** Imports inside the function body prevent circular imports across domain
   boundaries (`adoption → distribution → adoption`).

---

## Pre-flight Scan Before Mutation (All-or-Nothing)

Validate **all** preconditions before writing anything to the filesystem. If any check fails,
raise before touching any file.

**Used in `SyncEngine.sync_all()`:**
```python
# Validate ALL paths first — before any create_symlink() call
errors = [e for path in paths if (e := self.validate_path(path)) is not None]
if errors:
    raise OutOfWarehouseError(errors)

# Only now perform mutations
for path in paths:
    self.create_symlink(path)
```

**Used in `wire_agents_atomically()`:**
```python
# Pre-flight conflict scan: check ALL destinations for regular files
conflicts = [c for agent in agents if (c := _check_conflict(agent)) is not None]
if conflicts:
    raise RegularFileConflictError(conflicts=tuple(conflicts))
```

This ensures partial state (e.g., 3 of 10 symlinks created) never occurs on a validation error.

---

## Snapshot-Based Rollback for Per-Path State

When the pre-state of a path is non-trivial (symlink vs. missing vs. regular file), capture the
full state before touching it:

```python
# Pre-state capture
state = _snapshot_path(dest)  # returns ("missing",) | ("symlink", target) | ("regular_file",)
tool_snapshots.append((dest, *state))

# Rollback reconciliation
for path, kind, prior_target in reversed(tool_snapshots):
    if kind == "missing":
        path.unlink(missing_ok=True)
    elif kind == "symlink":
        path.unlink(missing_ok=True)
        path.symlink_to(prior_target)
    elif kind == "regular_file":
        pass  # never overwrote regular files; no action
```

---

## CLI Callback Closures

The `cli/sync.py` handler creates closures and injects them into `run_sync()`. This keeps
interactive prompting (Rich + Click) in the CLI layer while the domain orchestrator remains
non-interactive:

```python
@sync_cmd.command()
def sync(*, skip_git_check: bool, dry_run: bool) -> None:
    def _resolve(gap: SkillGap) -> bool:
        # Uses click.confirm — belongs in CLI layer
        return click.confirm(f"Add required skill {gap.skill!r}?")

    def _resolve_skill_conflicts(conflicts) -> list[str]:
        ...

    run_sync(project_root, _gap_resolver=_resolve, ...)
```

Domain function signature accepts `Callable` types, never importing Click directly (except
where waivered in `_TC10_WAIVERS`).

---

## Textual TUI Wrapped in Plain Class

The Textual `App` subclass is never exposed publicly. The public API is a plain wrapper with a
simple `run() -> Result` interface:

```python
class AdoptApp:
    def __init__(self, ...): ...
    def run(self) -> AdoptResult:
        inner = AdoptInnerApp(...)
        return inner.run()   # Textual App.run()

class AdoptInnerApp(App[AdoptResult]):
    ...
```

This decouples callers from Textual internals. Only `AdoptApp` is imported by the CLI.

---

## Error Hierarchy for Structured Error Context

Domain errors carry structured data beyond a message string:

- **`BeaconSyncError(hint: str | None)`** — carries a remediation hint rendered as a dim
  secondary line in the CLI.
- **`RegularFileConflictError(conflicts: tuple[AgentWireConflict, ...])`** — carries structured
  conflict info; the CLI calls `format_regular_file_conflict(e.conflicts)` to render a full
  remediation guide.

Always raise the most-specific subclass. The CLI catches in specificity order (most-specific
first) to handle each case appropriately.

---

## Git Subprocess Defensive Pattern

All git subprocess calls follow a defensive wrapper pattern:

```python
def _run_git(warehouse_path: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return result
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
```

Callers check for `None` return and treat it as "operation not available" rather than propagating
the subprocess error.

---

## Symlink Idempotency

All symlink creation is idempotent. The `SyncEngine.create_symlink()` method:

1. If the destination does not exist: create the symlink → returns `"created"`
2. If the destination is already a symlink pointing to the correct target: do nothing → returns
   `"ok"`
3. If the destination is a stale symlink (wrong target): unlink and recreate → returns
   `"updated"`
4. If the destination is a regular file: do nothing → returns `"skipped"` (migration case,
   handled separately)

Running `abc sync` multiple times on an already-synced project is always safe.

---

## Architecture Test as Enforcement Mechanism

`test_architecture.py` uses Python's `ast` module to enforce layering rules at the file level
without importing any production code. This is a **compile-time enforcement** pattern:

- No mocks, no fixtures, no `sys.path` manipulation.
- Walks all `.py` files under `beacon/` and parses their AST.
- Raises `AssertionError` with the specific violating file and import when a rule is broken.
- Waiver dictionaries (`_TC9B_WAIVERS`, `_TC10_WAIVERS`) are self-documenting and fail
  the test if a waiver becomes stale (referenced file/handler no longer exists).

New rules should be added to `test_architecture.py` with a new `TC` number and a comment
explaining what is being enforced and why.
