from ..types import Menu, Command, ChoiceArgument, FlagArgument, ValueArgument
from pprint import pprint
from ._base import OPTIONAL_ARGUMENTS

python_menu = Menu(
    name="Manage python versions and installations",
    arguments={},
    commands={
        "d": Command(
            name="dir",
            template=["uv", "python", "dir", OPTIONAL_ARGUMENTS],
            description="Show the uv Python installation directory",
        ),
        "f": Command(
            name="find",
            template=["uv", "python", "find", OPTIONAL_ARGUMENTS],
            description="Search for a Python installation",
        ),
        "i": Command(
            name="install",
            template=["uv", "python", "install", OPTIONAL_ARGUMENTS, ValueArgument(name="targets")],
            description="Download and install Python versions",
        ),
        "l": Command(
            name="list",
            template=["uv", "python", "list", OPTIONAL_ARGUMENTS],
            description="List the available Python installations",
        ),
        "p": Command(
            name="pin",
            template=["uv", "python", "pin", OPTIONAL_ARGUMENTS, ValueArgument(name="version")],
            description="Pin to a specific Python version",
        ),
        "u": Command(
            name="uninstall",
            template=[
                "uv",
                "python",
                "uninstall",
                OPTIONAL_ARGUMENTS,
                ValueArgument(name="targets")
            ],
            description="Uninstall Python versions",
        ),
    },
)


run_menu = Menu(
    name="Run a command or script",
    description="Ensures that the command runs in a Python environment",
    arguments={
        # Package options
        "--ae": FlagArgument(
            flag="--all-extras",
            description="Include all optional dependencies",
        ),
        "--ap": FlagArgument(
            flag="--all-packages",
            description="Run the command with all workspace members installed",
        ),
        "--ef": ValueArgument(
            name="--env-file",
            description="Load environment variables from a `.env` file",
        ),
        "-E": ValueArgument(
            name="--extra",
            description="Include optional dependencies from the specified extra name",
        ),
        "-g": ValueArgument(
            name="--group",
            description="Include dependencies from the specified dependency group",
        ),
        "-i": FlagArgument(
            flag="--isolated",
            description="Run the command in an isolated virtual environment",
        ),
        "-m": FlagArgument(
            flag="--module",
            description="Run a Python module",
        ),
        "--nd": FlagArgument(
            flag="--no-dev",
            description="Omit the development dependency group",
        ),
        "--ne": FlagArgument(
            flag="--no-editable",
            description="Install any editable dependencies as non-editable",
        ),
        "--nef": FlagArgument(
            flag="--no-env-file",
            description="Avoid reading environment variables from a `.env` file",
        ),
        "--ng": ValueArgument(
            name="--no-group",
            description="Exclude dependencies from the specified dependency group",
        ),
        "--od": FlagArgument(
            flag="--only-dev",
            description="Only include the development dependency group",
        ),
        "--og": ValueArgument(
            name="--only-group",
            description="Only include dependencies from the specified dependency group",
        ),
        "-p": ValueArgument(
            name="--package",
            description="Run the command in a specific package in the workspace",
        ),
        "-s": FlagArgument(
            flag="--script",
            description="Run the given path as a Python script",
        ),
        "-w": ValueArgument(
            name="--with",
            description="Run with the given packages installed",
        ),
        "--we": ValueArgument(
            name="--with-editable",
            description="Run with the given packages installed as editables",
        ),
        "--wr": ValueArgument(
            name="--with-requirements",
            description="Run with all packages listed in the given requirements.txt files",
        ),
    },
    commands={
    "r": Command(
        name="run",
        template=[
            "uv",
            "run",
            OPTIONAL_ARGUMENTS,
            "--",
            ValueArgument(name="command")
        ],
        description="Run the command",
    )},
)

main_menu = Menu(
    name="uv",
    arguments={
        # Global options
        "-f": ValueArgument(
            name="--config-file",
            description="The path to a `uv.toml` file to use for configuration",
            group="Global options",
        ),
        "-n": FlagArgument(
            flag="--no-cache",
            description="Avoid reading from or writing to the cache",
            group="Global options",
        ),
        "--nc": FlagArgument(
            flag="--no-config",
            description="Avoid discovering configuration files",
            group="Global options",
        ),
        "-o": FlagArgument(
            flag="--offline",
            description="Disable network access",
            group="Global options",
        ),
        "-p": ChoiceArgument(
            name="--python-preference",
            template="{self.name} {self.selected}",
            choices=["only-managed", "managed", "system", "only-system"],
            description="Whether to prefer uv-managed or system Python installations",
            group="Global options",
        ),
        "-q": FlagArgument(
            flag="--quiet",
            description="Do not print any output",
            group="Global options",
        ),
        "-v": FlagArgument(
            flag="--verbose",
            description="Use verbose output",
            group="Global options",
        ),
    },
    menus={
        "p": python_menu,
        "r": run_menu,
    },
)

if __name__ == "__main__":
    print(main_menu.model_dump_json(indent=2))
