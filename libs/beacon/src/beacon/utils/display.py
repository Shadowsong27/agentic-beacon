"""Display utility functions for Beacon CLI."""

import sys

from rich.console import Console

console = Console()


def is_interactive() -> bool:
    """Return True if running in an interactive terminal."""
    return sys.stdin.isatty()


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
