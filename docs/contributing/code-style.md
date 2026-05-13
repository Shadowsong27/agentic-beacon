# Code Style

This document covers coding conventions enforced in the Agentic Beacon codebase.

---

## Automated Formatting and Linting

All formatting and lint rules are enforced by **ruff** (configured in `pyproject.toml`). Running
`pre-commit` applies them automatically before each commit.

```bash
uv run ruff check --fix libs/beacon/src   # lint with auto-fix
uv run ruff format libs/beacon/src        # format
```

There is no separate type-checker (mypy/pyright) in CI. Type annotations are used for clarity
but not validated by tooling.

---

## Import Rules

These are strictly enforced by `test_architecture.py` (TC4, TC6, TC7):

### Absolute imports only

```python
# correct
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.adoption.models import AdoptCandidate

# wrong — relative imports are banned
from ..core.manifest import BeaconManifest
```

### Import from the defining module — never from `__init__.py`

`__init__.py` files are empty package markers (enforced by TC7). All symbols must be imported
from the file that defines them:

```python
# correct
from beacon.core.manifest.beacon import BeaconManifest

# wrong — imports from __init__.py
from beacon.core.manifest import BeaconManifest
```

### No private cross-module imports (TC6)

```python
# wrong — importing a private name from another module
from beacon.utils.git import _run_subprocess
```

### Import block order

1. `from __future__ import annotations` (when needed for forward references)
2. Standard library (`pathlib`, `subprocess`, `dataclasses`, etc.)
3. Third-party (`click`, `loguru`, `rich`, `pydantic`, `textual`)
4. Internal (`from beacon.core...`, `from beacon.domains...`, `from beacon.utils...`)

### Deferred (lazy) imports

Use deferred imports inside function bodies to break circular import cycles. This pattern is used
in `adoption/apply.py` and `adoption/delta.py`:

```python
def commit_session(...):
    # Deferred to avoid circular imports between adoption → distribution → adoption
    from beacon.core.manifest.beacon import BeaconManifest
    from beacon.domains.distribution.sync_engine import SyncEngine
    ...
```

This is an explicit choice — prefer top-level imports everywhere else.

---

## Type Annotations

- Annotate all function parameters and return types.
- Use `from __future__ import annotations` at the top of the file when forward references are
  needed (makes all annotations strings at runtime, enabling forward refs without quotes).
- Prefer `X | Y` union syntax (Python 3.10+) over `Optional[X]` or `Union[X, Y]`.
- Use `X | None` instead of `Optional[X]`.

---

## Function Signatures

All CLI handler functions use keyword-only parameters:

```python
@warehouse.command()
def connect(*, path: Path | None, main_branch: str | None) -> None:
    ...
```

This is a Click convention enforced throughout `cli/`. Domain and utility functions may use
positional parameters freely.

---

## Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Modules | `snake_case.py` | `sync_engine.py` |
| Classes | `PascalCase` | `SyncEngine`, `BeaconManifest` |
| Functions / methods | `snake_case` | `create_symlink`, `run_sync` |
| Constants | `UPPER_SNAKE_CASE` | `_TC9B_WAIVERS`, `ABC_DEBUG` |
| Private helpers | `_leading_underscore` | `_run_git`, `_collect_domain_symbols` |
| Test helpers | `_leading_underscore` | `_make_warehouse`, `_noop_sync` |
| Pydantic model fields | `snake_case` | `local_path`, `main_branch` |

---

## Docstrings

No enforced docstring style. Add module-level docstrings to explain non-obvious responsibilities.
Function docstrings are optional but encouraged for public domain functions that have subtle
preconditions or side effects.

---

## Error Handling

Raise exceptions from the `beacon.core.exceptions` hierarchy rather than built-in exceptions:

```python
from beacon.core.exceptions import BeaconSyncError, ConfigurationError

# Prefer typed exceptions for all domain errors
raise BeaconSyncError("message", hint="how to fix it")

# Only raise built-in exceptions (ValueError, TypeError) for low-level validation
# where no Beacon-specific context is needed
```

Do not call `sys.exit()` from domain code. That belongs in the `cli/` layer only.

---

## Rich Output

All terminal output uses `rich.Console`. Never use `print()` directly:

```python
from rich.console import Console
console = Console()

console.print("[green]Done[/green]")
console.print(f"[red]Error:[/red] {message}")
```

Rich console output belongs in `cli/` handlers. Domain functions return structured data; the CLI
layer formats and prints it.

---

## Data Classes vs. Pydantic Models

Use **Pydantic `BaseModel`** when:
- The data is loaded from or written to a file (YAML, TOML, JSON)
- Field-level validation is needed
- Serialization/deserialization is part of the interface

Use **`@dataclass`** when:
- The object is a service object (e.g., `SyncEngine`) or an in-memory aggregate
- No serialization is required
- Simpler mutation semantics are preferred

---

## Convention for `__init__.py`

All `__init__.py` files are **empty package markers**. They may contain only a module docstring or
be completely empty. No re-exports, no `__all__`, no logic. This is enforced by TC7 in
`test_architecture.py`.
