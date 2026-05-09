"""Display utility functions for Beacon CLI."""

import os
import sys
from collections.abc import Sequence
from pathlib import Path

from rich.console import Console

console = Console()


def is_interactive() -> bool:
    """Return True if running in an interactive terminal."""
    return sys.stdin.isatty()


def format_regular_file_conflict(conflicts: Sequence) -> str:
    """Return a Rich-markup string listing all conflicting paths with remediation steps.

    Each element must expose .dest (Path), .agent_name (str), .tool (str).
    Pure function — no I/O, no side effects.
    """

    def _rel(dest: Path) -> Path:
        try:
            rel = Path(os.path.relpath(dest))
            if str(rel).startswith(".."):
                return dest
            return rel
        except ValueError:
            return dest

    n = len(conflicts)
    s = "s" if n != 1 else ""
    rel_dests = [_rel(c.dest) for c in conflicts]

    lines: list[str] = [
        f"[red]✗ Cannot wire {n} agent{s} (regular file conflict):[/red]",
    ]
    for rel in rel_dests:
        lines.append(f"  • {rel} (project-local content)")

    lines.append("")
    lines.append("Resolution options (pick one):")
    lines.append("  1) Remove the local file:")
    for rel in rel_dests:
        lines.append(f"       rm {rel}")
    lines.append("  2) Back up and let Beacon manage it:")
    for rel in rel_dests:
        user_md = rel.parent / f"{rel.stem}.user.md"
        lines.append(f"       mv {rel} {user_md}")
    lines.append("  3) Drop the agent from beacon.yaml.artifacts.agents and re-run:")
    lines.append("       abc adopt    # then 'reject' the listed agent(s)")

    return "\n".join(lines)


def print_doctor_summary(issues: list[str], fixes_applied: list[str]) -> None:
    console.print()
    if fixes_applied:
        console.print(f"[green]Applied {len(fixes_applied)} fix(es):[/green]")
        for f in fixes_applied:
            console.print(f"  {f}")
        console.print()
    if not issues:
        console.print("[bold green]Everything looks good.[/bold green]")
    else:
        count = len(issues)
        console.print(
            f"[bold yellow]{count} issue(s) found.[/bold yellow]"
            + (
                " Run [bold]abc doctor --fix[/bold] to repair fixable issues."
                if any("file-level" in i for i in issues)
                else ""
            )
        )
