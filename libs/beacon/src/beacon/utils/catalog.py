"""Warehouse catalog utility functions for Beacon CLI."""

from pathlib import Path

from rich.console import Console

from beacon.core.manifest.beacon import BeaconManifest

console = Console()


def _generate_warehouse_catalog(warehouse_path: Path) -> str:
    """Scan warehouse and generate markdown catalog for AI agents.

    Args:
        warehouse_path: Path to warehouse directory

    Returns:
        Markdown-formatted catalog string
    """
    lines = [
        "# Warehouse Artifact Catalog",
        "",
        "This catalog lists all available artifacts in the connected warehouse.",
        "Use this to decide which artifacts to add to your project's beacon.yaml.",
        "",
        f"**Warehouse:** `{warehouse_path}`",
        "",
    ]

    for section_name, section_dir in [
        ("Knowledge", "knowledge"),
        ("Skills", "skills"),
        ("Contexts", "contexts"),
    ]:
        section_path = warehouse_path / section_dir
        if not section_path.exists():
            continue

        lines.append(f"## {section_name}")
        lines.append("")
        lines.append(
            f"Paths are relative to warehouse root. Use in beacon.yaml under `artifacts.{section_dir}`."
        )
        lines.append("")

        # Scan for files
        files = sorted(section_path.rglob("*"))
        file_entries = []
        for f in files:
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(warehouse_path)
                # Try to extract description from first line
                desc = _extract_description(f)
                if desc:
                    file_entries.append(f"- `{rel}` - {desc}")
                else:
                    file_entries.append(f"- `{rel}`")

        if file_entries:
            lines.extend(file_entries)
        else:
            lines.append("_No artifacts found._")

        lines.append("")

    lines.extend(
        [
            "## Usage",
            "",
            "Add paths to your `.agentic-beacon/beacon.yaml` file:",
            "",
            "```yaml",
            "artifacts:",
            "  knowledge:",
            "    - knowledge/languages/python/**/*.md  # Glob pattern",
            "    - knowledge/infrastructure/docker-standards.md  # Specific file",
            "  skills:",
            "    - skills/code-review/",
            "  contexts:",
            "    - contexts/README.md",
            "```",
            "",
            "Then run `abc sync` to download the artifacts.",
            "",
        ]
    )

    return "\n".join(lines)


def _extract_description(file_path: Path) -> str:
    """Extract a brief description from a file's first heading or content.

    Args:
        file_path: Path to the file

    Returns:
        Description string, or empty string if none found
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines()[:5]:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line.startswith("description:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _register_in_beacon_yaml(
    beacon_settings: BeaconManifest, beacon_yaml: Path, file_path: str
) -> bool:
    """Add an explicit path to beacon.yaml under the appropriate artifact type.

    Returns True if the file was added (i.e. it wasn't already listed explicitly).
    """
    from .delta import _infer_artifact_type

    artifact_type = _infer_artifact_type(file_path)
    if artifact_type is None:
        return False

    current_list: list[str] = getattr(beacon_settings.artifacts, artifact_type)
    if file_path not in current_list:
        current_list.append(file_path)
        beacon_settings.to_yaml(beacon_yaml)
        return True
    return False
