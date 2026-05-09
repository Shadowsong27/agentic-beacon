"""Free-function artifact listing — reads artifacts_path without requiring SyncEngine."""

from pathlib import Path


def list_artifacts(
    artifacts_path: Path, artifact_type: str | None = None
) -> dict[str, list[str]]:
    """List synced artifacts by type.

    Args:
        artifacts_path: Path to the .agentic-beacon/artifacts/ directory.
        artifact_type: Restrict to this section; omit to list contexts and skills.

    Returns:
        Dict mapping section name to sorted list of relative paths.
    """
    types_to_show = [artifact_type] if artifact_type else ["contexts", "skills"]
    result: dict[str, list[str]] = {}
    for section in types_to_show:
        section_dir = artifacts_path / section
        if not section_dir.exists():
            continue
        files = sorted(
            str(f.relative_to(artifacts_path))
            for f in section_dir.rglob("*")
            if f.is_symlink() and not f.name.startswith(".")
        )
        if files:
            result[section] = files
    return result
