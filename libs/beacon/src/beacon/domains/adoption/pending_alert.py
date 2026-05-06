"""Pre-command pending artifact alert for the abc CLI.

Emits a one-line stderr notice when .agentic-beacon/pending.yaml is non-empty,
so users are prompted to run `abc adopt` after authoring new artifacts.

The check is suppressed outside a project (no .agentic-beacon/config.toml
found via cwd-walk) and never raises — it must not block subcommand execution.
"""

import sys
from pathlib import Path

from loguru import logger

from beacon.core.manifest.pending import PendingManifest


def _find_project_root(cwd: Path) -> Path | None:
    current = cwd.resolve()
    while True:
        if (current / ".agentic-beacon" / "config.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def maybe_emit_pending_alert(cwd: Path) -> None:
    """Print a stderr notice if the current project has pending artifacts.

    Walks up from *cwd* looking for .agentic-beacon/config.toml to determine
    project root. Silently returns if not inside a project or if pending.yaml
    is absent / empty.
    """
    try:
        project_root = _find_project_root(cwd)
        if project_root is None:
            return

        pending_path = project_root / ".agentic-beacon" / "pending.yaml"
        manifest = PendingManifest.from_yaml(pending_path)
        count = len(manifest.pending)
        if count > 0:
            print(
                f"⚠ {count} pending artifacts. Run 'abc adopt' to wire them.",
                file=sys.stderr,
            )
    except Exception as e:
        logger.debug("Pending alert check failed: {}", e)
