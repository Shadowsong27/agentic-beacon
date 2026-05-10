"""Cross-domain primitive for managing the .agentic-beacon project directory."""

from pathlib import Path


def ensure_beacon_dir(project_root: Path) -> Path:
    """Ensure .agentic-beacon directory exists, creating it if necessary.

    Returns the path to the beacon directory.
    """
    beacon_dir = project_root / ".agentic-beacon"
    beacon_dir.mkdir(exist_ok=True)
    return beacon_dir
