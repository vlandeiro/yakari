from rich.text import Text
from rich.table import Table
from rich.style import Style
from rich.padding import Padding

from .types import (
    Prefix,
    Menu,
    Command,
    Argument,
    FlagArgument,
    ChoiceArgument,
    ValueArgument,
)

TABLE_CONFIG = dict(
    show_header=False,
    box=None,
    title_justify="left",
)
TABLE_PADDING = (1, 0)
DIM_STYLE = Style(dim=True)
ENABLED_STYLE = Style(color="green", italic=True)
HIGHLIGHT_STYLE = Style(bold=True)


def should_dim(key: str, user_input: str) -> str:
    return not key.startswith(user_input)


def render_command(command: Command) -> str:
    return command.description or command.name


def render_argument(argument: Argument) -> str:
    match argument:
        case FlagArgument():
            return argument.name
        case ChoiceArgument():
            choices_str = " | ".join(argument.choices)
            choices_str = f"( {choices_str} )"
            if argument.selected:
                choices_str = Text(choices_str)
                choices_str.highlight_words([f" {argument.selected} "], HIGHLIGHT_STYLE)
            return Text.assemble(argument.name, " ", choices_str)
        case ValueArgument():
            if argument.value is None:
                argument_repr = ""
            elif argument.value == "":  # special case for a valid empty string input
                argument_repr = '""'
            else:
                argument_repr = argument.value
            return f"{argument.name}={argument_repr}"
        case _:
            raise ValueError(f"{argument} of type {type(argument)} is not supported.")


def render_key(key: str, user_input: str) -> str:
    if user_input:
        if key.startswith(user_input):
            key = Text.assemble(
                (user_input, HIGHLIGHT_STYLE), key.split(user_input, 1)[-1]
            )
        else:
            key = Text(key)
    return key


def render_menu(menu: Menu):
    yield Text(menu.name, style="bold")
    table = Table("key", "prefix", **TABLE_CONFIG)
    for key, prefix in menu.prefixes.items():
        table.add_row(key, prefix.name)
    yield Padding(table, TABLE_PADDING)


def render_prefix(prefix: Prefix, user_input: str):
    yield Text(prefix.name, style="bold")
    if prefix.arguments:
        table = Table("key", "name", "desc", title="Arguments", **TABLE_CONFIG)
        for key, argument in prefix.arguments.items():
            style = None
            if argument.enabled:
                style = ENABLED_STYLE
            elif should_dim(key, user_input):
                style = DIM_STYLE

            key = render_key(key, user_input)
            table.add_row(key, render_argument(argument), style=style)
        yield Padding(table, TABLE_PADDING)

    if prefix.commands:
        table = Table("key", "name", title="Commands", **TABLE_CONFIG)
        for key, command in prefix.commands.items():
            table.add_row(key, render_command(command))
        yield Padding(table, TABLE_PADDING)
