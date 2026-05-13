# Configuration System

This file documents how Agentic Beacon is configured at runtime — environment variables, workspace config files, and the manifest models that drive behavior.

← [Back to CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## Configuration Sources

There are three distinct configuration layers. They do not overlap and have no precedence ordering — each one governs a separate concern.

| Source | File / Mechanism | Governs |
|---|---|---|
| **Runtime settings** | `ABC_*` environment variables | CLI tool behavior (lookback depth, global agent dir, debug mode) |
| **Workspace config** | `.agentic-beacon/config.toml` | Per-project warehouse connection (path, branch) |
| **Beacon manifest** | `beacon.yaml` | Which artifacts a project has adopted |
| **Pending manifest** | `.agentic-beacon/pending.yaml` | Artifacts authored but not yet wired into beacon.yaml |

---

## Runtime Settings (`core/settings.py`)

Implemented as a Pydantic `BaseSettings` subclass. All settings use the `ABC_` prefix, resolved from environment variables at import time.

```python
# Singleton loaded at import time
from beacon.core.settings import abc_settings
```

| Variable | Type | Default | Description |
|---|---|---|---|
| `ABC_GLOBAL_AGENTS_DIR` | `Path` | `~/.abc/agents` | Override the global directory where agent symlinks are installed |
| `ABC_MAX_COMMITS_LOOKBACK` | `int` | `100` (min: 1) | Max git commits to scan when computing `commits_ago` for warehouse artifacts |
| `ABC_DEBUG` | `bool` | `false` | Enable debug-level logging in the loguru sink |

Nested delimiter is `__` (double underscore). To override a nested path: `ABC_WAREHOUSE__LOCAL_PATH=/path/to/wh`.

---

## Workspace Config (`.agentic-beacon/config.toml`)

Created by `abc warehouse connect` and read by every command that needs to locate the warehouse. It lives at `.agentic-beacon/config.toml` relative to the project root.

**Format:**
```toml
[warehouse]
local_path = "/absolute/path/to/my-org-warehouse"
main_branch = "main"
```

**Implemented as:** `core/manifest/workspace.py::WorkspaceConfig` — a `pydantic-settings` `BaseSettings` with a `TomlConfigSettingsSource`. It reads only from TOML (no env var override). The settings source is overridden to exclusively use the TOML file; missing file raises `ValidationError` (not silently ignored).

**Validation rules:**
- `local_path` must be an absolute path
- `main_branch` is validated against a strict git branch name regex that rejects dangerous values (e.g. `"."` would become `git checkout .`)

---

## Beacon Manifest (`beacon.yaml`)

The primary per-project artifact registry. Managed by `abc adopt` and `abc sync`.

**Format:**
```yaml
artifacts:
  contexts:
    - contexts/coding-standards.md
  skills:
    - skills/record-knowledge
    - skills/record-skill
  agents:
    - agents/my-agent.md
ignore:
  skills:
    - skills/private-*
```

**Model:** `core/manifest/beacon.py::BeaconManifest`

Key behaviors:
- Uses `yaml.safe_load` (never `yaml.load`)
- `artifacts` section uses `model_config = {"extra": "forbid"}` — unknown keys raise `ValidationError`
- Auto-migrates legacy `artifacts.knowledge` key: removes it transparently and rewrites the file
- `ignore.skills` supports fnmatch glob patterns for excluding skills from `abc warehouse status/contribute` diffs

---

## Pending Manifest (`.agentic-beacon/pending.yaml`)

Tracks artifacts authored in the current project via skills (`record-knowledge`, `record-skill`) but not yet wired into `beacon.yaml`. It is gitignored and managed by the skill scripts and `abc adopt`.

**Format:**
```yaml
pending:
  - path: skills/my-new-skill
    type: skill
    action: add
    source: record-skill
    created_at: "2026-05-06T12:00:00Z"
```

**Model:** `core/manifest/pending.py::PendingManifest`

Key behaviors:
- `from_yaml` is tolerant: missing file returns an empty manifest (not an error) — so `abc adopt` works even on projects with no pending entries
- Datetime format is always UTC, always `%Y-%m-%dT%H:%M:%SZ`
- Field order is explicitly preserved in `to_yaml` serialization: `path / type / action / source / created_at`
- `PendingEntry.type` uses `Literal["skill", "context", "agent"]`

---

## Agent Manifest (`agents/agents.yaml` in the warehouse)

Declares which skills each agent requires. Lives in the warehouse's `agents/` directory, not in the project.

**Format:**
```yaml
my-agent:
  requires:
    - skills/record-knowledge
```

Used by:
- `abc sync` to validate all agent dependencies are adopted before syncing
- `abc adopt` TUI to auto-propagate skill selections when an agent is ticked

**Model:** `core/dependencies/manifest.py`

---

## How Configuration is Read in Practice

When a command runs:

1. `cli/main.py` fires — `abc_settings` is already loaded from the module singleton
2. `ensure_sync_ready(project_root)` is called (in distribution/warehouse commands) — this reads `.agentic-beacon/config.toml` via `WorkspaceConfig` and returns `(warehouse_path, beacon_settings)`
3. `BeaconManifest.from_yaml(beacon_yaml_path)` loads `beacon.yaml`
4. Domain functions receive concrete `Path` objects and parsed model instances — they do not re-read config themselves

This means configuration is always loaded at the CLI layer boundary, then passed down as typed values. Domain functions are pure with respect to configuration loading.
