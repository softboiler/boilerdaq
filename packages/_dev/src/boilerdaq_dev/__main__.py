"""Command-line interface."""

from cappa.base import command, invoke
from cappa.subcommand import Subcommands


@command(invoke="boilerdaq_dev.tools.add_change")
class AddChange:
    """Add change."""


@command(invoke="boilerdaq_dev.tools.get_actions")
class GetActions:
    """Get actions used by this repository."""


@command(invoke="boilerdaq_dev.tools.sync_local_dev_configs")
class SyncLocalDevConfigs:
    """Synchronize local dev configs."""


@command(invoke="boilerdaq_dev.tools.elevate_pyright_warnings")
class ElevatePyrightWarnings:
    """Elevate Pyright warnings to errors."""


@command()
class Dev:
    """Dev tools."""

    commands: Subcommands[
        AddChange | GetActions | SyncLocalDevConfigs | ElevatePyrightWarnings
    ]


def main():
    """CLI entry-point."""
    invoke(Dev)


if __name__ == "__main__":
    main()
