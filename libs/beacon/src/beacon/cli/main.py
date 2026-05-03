"""Main Click group and command registration for the abc CLI."""

import sys

import click
from loguru import logger

from beacon.cli.adoption import adopt
from beacon.cli.agent import agents, install_artifact, list_cmd
from beacon.cli.diagnostics import doctor
from beacon.cli.setup import setup
from beacon.cli.sync import clean, reset_cmd, status, sync, update
from beacon.cli.warehouse import warehouse


@click.group()
@click.version_option(package_name="agentic-beacon")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def main(*, verbose: bool) -> None:
    """Agentic Beacon CLI (abc) - Guide your agents with distributed knowledge."""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


# Register all commands
main.add_command(warehouse)
main.add_command(setup)
main.add_command(sync)
main.add_command(agents)
main.add_command(install_artifact, name="install")
main.add_command(reset_cmd, name="reset")
main.add_command(update, name="update")
main.add_command(list_cmd, name="list")
main.add_command(clean)
main.add_command(status)
main.add_command(adopt)
main.add_command(doctor)


@click.command()
@click.pass_context
def contribute(ctx) -> None:
    """[Removed] Use 'abc warehouse contribute' instead."""
    click.echo(
        "Error: 'abc contribute' has been removed.\n"
        "Use 'abc warehouse contribute' instead.",
        err=True,
    )
    sys.exit(1)


@click.command()
@click.pass_context
def delta(ctx) -> None:
    """[Removed] Use 'abc warehouse status' instead."""
    click.echo(
        "Error: 'abc delta' has been removed.\nUse 'abc warehouse status' instead.",
        err=True,
    )
    sys.exit(1)


main.add_command(contribute)
main.add_command(delta)


if __name__ == "__main__":
    main()
