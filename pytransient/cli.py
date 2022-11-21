import pkgutil
import subprocess

import click
import structlog

from .app import PyTransientApp, TransientKeymapWidget
from .models import Transient


log = structlog.get_logger()


@click.command()
@click.argument("command-name")
def main(command_name: str):
    tw = TransientKeymapWidget(id="transient")
    tw.transient = Transient.from_command_name(command_name)
    app = PyTransientApp()
    app.transient_widget = tw
    cmd = app.run()

    if cmd:
        cmd_str = " ".join(cmd)
        print(f"Running '{cmd_str}'")
        # subprocess.run(cmd)
        subprocess.run(["echo", *cmd])


if __name__ == "__main__":
    main()
