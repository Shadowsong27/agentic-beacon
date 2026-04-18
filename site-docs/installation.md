# Installation

## Requirements

- **Python 3.12 or higher**
- One of: `uv`, `pipx`, or `pip`

## Install Methods

=== "uv (Recommended)"

    ```bash
    uv tool install agentic-beacon
    ```

    `uv tool install` creates an isolated environment and puts `abc` on your PATH. Best for tools you want available everywhere.

=== "pipx"

    ```bash
    pipx install agentic-beacon
    ```

    `pipx` is equivalent to `uv tool install` for isolated tool environments.

=== "pip"

    ```bash
    pip install agentic-beacon
    ```

    Use this if you're installing into an existing virtual environment.

=== "Offline / Air-gapped"

    Download a platform bundle from the [GitHub Releases page](https://github.com/Shadowsong27/agentic-beacon/releases) and install from the local file:

    ```bash
    pip install agentic-beacon-*.whl
    ```

## Verify

```bash
abc --version
```

You should see the current version (`2.5.0` or higher).

## Upgrade

=== "uv"

    ```bash
    uv tool upgrade agentic-beacon
    ```

=== "pipx"

    ```bash
    pipx upgrade agentic-beacon
    ```

=== "pip"

    ```bash
    pip install --upgrade agentic-beacon
    ```

## What Gets Installed

Installing `agentic-beacon` puts a single command on your PATH:

| Command | Description |
|---------|-------------|
| `abc` | The Agentic Beacon CLI — the only command you need |

All subcommands (`abc sync`, `abc warehouse init`, etc.) are available under `abc`.

## Next Steps

→ **[Quick Start](quickstart.md)** — set up a warehouse and connect your first project in minutes.
