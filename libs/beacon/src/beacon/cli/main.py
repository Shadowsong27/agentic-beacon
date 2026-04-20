"""Main Click group and command registration for the abc CLI."""

import sys

import click
from loguru import logger

from beacon.cli.adoption import adopt
from beacon.cli.agent import agents, install_artifact, list_cmd
from beacon.cli.contribute import contribute
from beacon.cli.diagnostics import doctor
from beacon.cli.setup import setup
from beacon.cli.sync import clean, delta, reset_cmd, status, sync, update
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
main.add_command(delta)
main.add_command(contribute)
main.add_command(reset_cmd, name="reset")
main.add_command(update, name="update")
main.add_command(list_cmd, name="list")
main.add_command(clean)
main.add_command(status)
main.add_command(adopt)
main.add_command(doctor)


if __name__ == "__main__":
    main()
