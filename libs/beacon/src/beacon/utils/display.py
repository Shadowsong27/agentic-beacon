"""Display utility functions for Beacon CLI."""

import sys

import click
from rich.console import Console

console = Console()


def _handle_soft_block(
    conflicts: list[str],
    force: bool,
    preserve: bool,
) -> bool:
    """Handle soft-block pre-check for conflicting files.

    Returns True if we should proceed with overwriting, False to skip conflicts.
    May call sys.exit(1) in non-interactive mode when conflicts exist without flags.

    Args:
        conflicts: List of relative paths that have conflicting local content
        force: --force flag (overwrite without prompt)
        preserve: --preserve flag (skip without prompt)

    Returns:
        True to proceed (overwrite), False to skip (preserve)
    """
    if not conflicts:
        return True  # No conflicts — proceed normally

    if preserve:
        return False  # --preserve: skip all conflicts silently

    if force:
        return True  # --force: overwrite all conflicts silently

    # Interactive vs non-interactive
    is_interactive = sys.stdin.isatty()

    conflict_list = "\n".join(f"  • {p}" for p in conflicts)
    console.print(
        f"\n[yellow]Warning:[/yellow] {len(conflicts)} file(s) have local changes "
        f"that differ from the warehouse:\n{conflict_list}\n"
    )

    if not is_interactive:
        console.print(
            "[red]Error:[/red] Non-interactive mode — cannot prompt for overwrite.\n"
            "Use --force to overwrite or --preserve to skip conflicting files."
        )
        sys.exit(1)

    answer = click.confirm(
        "Overwrite these files with warehouse content?", default=False
    )
    return answer


def _interactive_select(
    prompt: str, options: list[str], *, default_all: bool = False
) -> list[str]:
    """Interactive selection of options."""
    if not options:
        return []

    console.print(f"\n[bold]{prompt}[/bold]")
    console.print(
        "[dim]Enter numbers separated by commas, or 'all' for all options[/dim]"
    )

    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option}")

    if default_all:
        default_text = " [default: all]"
    else:
        default_text = ""

    selection = click.prompt(
        f"\nSelection{default_text}",
        default="all" if default_all else "",
        show_default=False,
    )

    if selection.lower() == "all":
        return options

    if not selection:
        return []

    # Parse comma-separated numbers
    try:
        indices = [int(x.strip()) for x in selection.split(",")]
        return [options[i - 1] for i in indices if 1 <= i <= len(options)]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection. Using none.[/red]")
        return []


def _print_doctor_summary(issues: list[str], fixes_applied: list[str]) -> None:
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
