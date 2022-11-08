import pkgutil
import subprocess

import click
import structlog

from .app import PyTransientApp
from .config import Config

log = structlog.get_logger()


@click.command()
@click.argument("command-name")
@click.option("--entry-point")
def main(command_name: str, entry_point: str = None):
    config = Config.from_command_name(command_name)
    entry_point = entry_point or command_name

    if entry_point not in config.actions:
        log.error(
            f"Action '{entry_point}' is not available in the loaded config. "
            "With this config file, you must use one of the following actions: "
            f"{set(config.keys())}."
        )
        sys.exit(1)

    action = config.actions[entry_point]
    app = PyTransientApp(action)
    cmd = app.run()

    if cmd:
        cmd_str = " ".join(cmd)
        print(f"Running '{cmd_str}'")
        subprocess.run(["echo", *cmd])


if __name__ == "__main__":
    main()
