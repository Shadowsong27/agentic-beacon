"""Context commands for the abc CLI."""

import json
from pathlib import Path

import click

from beacon.domains.warehouse.context_index import ContextIndexError, index_contexts
from beacon.domains.warehouse.warehouse_read import (
    InvalidNameError,
    ItemMissingError,
    WarehouseReadError,
    read_contexts,
    read_decision_rules,
    read_intake_policy,
    read_operate_profile,
)

WAREHOUSE_OPTION = click.option(
    "--warehouse",
    type=click.Path(path_type=Path),
    default=None,
    help="Warehouse git repository. Defaults to the connected warehouse.",
)
REF_OPTION = click.option(
    "--ref",
    default="HEAD",
    show_default=True,
    help="Commit-ish to read. The output names the full SHA it resolves to.",
)


@click.group(name="context")
def context() -> None:
    """Inspect the contexts of a warehouse."""


@context.command(name="index")
@WAREHOUSE_OPTION
@REF_OPTION
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


@context.command(name="show")
@click.argument("names", nargs=-1, required=True)
@WAREHOUSE_OPTION
@REF_OPTION
def context_show(*, names: tuple[str, ...], warehouse: Path | None, ref: str) -> None:
    """Print the committed text of one or more contexts as JSON.

    NAMES are context names without the .md suffix (teams/x for
    contexts/teams/x.md). Exits 3 if any name is missing at the commit.

    Example:
        abc context show alpha teams/beta
    """
    try:
        result = read_contexts(warehouse, ref, Path.cwd(), list(names))
    except InvalidNameError as exc:
        raise click.BadParameter(str(exc)) from exc
    except ItemMissingError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(3) from exc
    except WarehouseReadError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(1) from exc
    for warning in result.warnings:
        click.echo(f"warning: {warning}", err=True)
    click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


@context.command(name="intake-policy")
@click.argument("board")
@WAREHOUSE_OPTION
@REF_OPTION
def context_intake_policy(*, board: str, warehouse: Path | None, ref: str) -> None:
    """Print the intake policy context of a board as JSON.

    Reads contexts/intake-policy-BOARD.md. Exits 3 if it is missing.

    Example:
        abc context intake-policy AB
    """
    try:
        result = read_intake_policy(warehouse, ref, Path.cwd(), board)
    except InvalidNameError as exc:
        raise click.BadParameter(str(exc)) from exc
    except ItemMissingError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(3) from exc
    except WarehouseReadError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(1) from exc
    for warning in result.warnings:
        click.echo(f"warning: {warning}", err=True)
    click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


@context.command(name="operate-profile")
@click.argument("domain")
@WAREHOUSE_OPTION
@REF_OPTION
def context_operate_profile(*, domain: str, warehouse: Path | None, ref: str) -> None:
    """Print the operate profile context of a domain as JSON.

    Reads contexts/operate-DOMAIN.md. Exits 3 if it is missing.

    Example:
        abc context operate-profile airflow-platform
    """
    try:
        result = read_operate_profile(warehouse, ref, Path.cwd(), domain)
    except InvalidNameError as exc:
        raise click.BadParameter(str(exc)) from exc
    except ItemMissingError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(3) from exc
    except WarehouseReadError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(1) from exc
    for warning in result.warnings:
        click.echo(f"warning: {warning}", err=True)
    click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


@context.command(name="decision-rules")
@WAREHOUSE_OPTION
@REF_OPTION
def context_decision_rules(*, warehouse: Path | None, ref: str) -> None:
    """Print the ## Decision rules section of every context as JSON.

    A context with no such section is left out. No sections is not an error.

    Example:
        abc context decision-rules
    """
    try:
        result = read_decision_rules(warehouse, ref, Path.cwd())
    except WarehouseReadError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
