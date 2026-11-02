"""Context commands for the abc CLI."""

import json
from pathlib import Path

import click

from beacon.domains.warehouse.context_index import ContextIndexError, index_contexts


@click.group(name="context")
def context() -> None:
    """Inspect the contexts of a warehouse."""


@context.command(name="index")
@click.option(
    "--warehouse",
    type=click.Path(path_type=Path),
    default=None,
    help="Warehouse git repository. Defaults to the connected warehouse.",
)
@click.option(
    "--ref",
    default="HEAD",
    show_default=True,
    help="Commit-ish to index. The output names the full SHA it resolves to.",
)
def context_index(*, warehouse: Path | None, ref: str) -> None:
    """Print the contexts at a warehouse commit as JSON.

    Reads committed content at the ref, not the working tree. Warnings go to
    stderr; the JSON goes to stdout.

    Example:
        abc context index
        abc context index --warehouse ~/warehouse --ref v1.2.0
    """
    try:
        index = index_contexts(warehouse, ref, Path.cwd())
    except ContextIndexError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(1) from exc
    for warning in index.warnings:
        click.echo(f"warning: {warning}", err=True)
    click.echo(json.dumps(index.to_dict(), indent=2, ensure_ascii=False))
