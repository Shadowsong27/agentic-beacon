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

    Download the wheel from the [GitHub Releases page](https://github.com/Shadowsong27/agentic-beacon/releases), then install it as a tool from the local file:

    ```bash
    uv tool install ./agentic-beacon-*.whl
    ```

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
