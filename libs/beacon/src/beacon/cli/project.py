"""Project commands for the abc CLI."""

import json
from pathlib import Path

import click

from beacon.domains.setup.project_instructions import read_project_instructions
from beacon.domains.warehouse.warehouse_read import ItemMissingError, WarehouseReadError


@click.group(name="project")
def project() -> None:
    """Inspect a project repository."""


@project.command(name="instructions")
@click.option(
    "--repo",
    type=click.Path(path_type=Path),
    default=".",
    show_default=True,
    help="Project git repository. Any path inside it works.",
)
@click.option(
    "--ref",
    default="HEAD",
    show_default=True,
    help="Commit-ish to read. The output names the full SHA it resolves to.",
)
def project_instructions(*, repo: Path, ref: str) -> None:
    """Print the root AGENTS.md at a commit, with beacon import lines removed.

    Reads committed content at the ref, not the working tree. Lines that import
    beacon-owned artifacts are removed and listed in "removed". Exits 3 if
    AGENTS.md is missing at the commit.

    Example:
        abc project instructions
        abc project instructions --repo ~/code/app --ref v2.0.0
    """
    try:
        result = read_project_instructions(repo, ref)
    except ItemMissingError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(3) from exc
    except WarehouseReadError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
