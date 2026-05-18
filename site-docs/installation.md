# Installation

## Requirements

- **Python 3.12 or higher**
- `uv` — [install uv](https://docs.astral.sh/uv/getting-started/installation/)

## Install

```bash
uv tool install agentic-beacon
```

`uv tool install` creates an isolated environment and puts `abc` on your PATH globally — no virtual environment activation needed.

=== "Offline / Air-gapped"

    Each GitHub release attaches a per-platform **offline bundle** (`agentic_beacon-<version>-bundle-<platform>.zip`) containing the package wheel plus every transitive dependency. Install from the bundle without touching PyPI:

    ```bash
    # 1. Download the bundle for your platform from the GitHub Releases page,
    #    e.g. agentic_beacon-3.4.0-bundle-linux-x86_64.zip
    unzip agentic_beacon-3.4.0-bundle-linux-x86_64.zip -d ./bundle

    # 2. Install from the local wheel directory (no PyPI access required)
    uv tool install --reinstall --no-index --find-links ./bundle agentic-beacon
    ```

    Flag rationale:

    - `--no-index` — disable PyPI lookup so `uv` never reaches the network.
    - `--find-links ./bundle` — resolve every wheel (package + deps) from the unzipped bundle.
    - `--reinstall` — force a clean install even if a cached version is present (otherwise `uv` may silently no-op).

    Bare `uv tool install ./agentic-beacon-*.whl` won't work because the wheel still needs its dependencies resolved, which falls back to PyPI.

## Verify

```bash
abc --version
```

You should see a version number printed (e.g. `3.x.y`).

## Upgrade

```bash
uv tool upgrade agentic-beacon
```

## What Gets Installed

Installing `agentic-beacon` puts a single command on your PATH:

| Command | Description |
|---------|-------------|
| `abc` | The Agentic Beacon CLI — the only command you need |

All subcommands (`abc sync`, `abc warehouse init`, etc.) are available under `abc`.

## Next Steps

→ **[Quick Start](quickstart.md)** — set up a warehouse and connect your first project in minutes.
