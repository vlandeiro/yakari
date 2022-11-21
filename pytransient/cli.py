import pkgutil
import subprocess

import click
import structlog

from .app import PyTransientApp
from .models import Transient

log = structlog.get_logger()


@click.command()
@click.argument("command-name")
def main(command_name: str):
    transient = Transient.from_command_name(command_name)
    app = PyTransientApp(transient)
    cmd = app.run()

    if cmd:
        cmd_str = " ".join(cmd)
        print(f"Running '{cmd_str}'")
        subprocess.run(cmd)


if __name__ == "__main__":
    main()
