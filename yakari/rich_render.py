from collections import defaultdict
from typing import DefaultDict, List, Tuple

from rich.padding import Padding
from rich.style import Style
from rich.table import Column, Table
from rich.text import Text
from textual import log

from .types import (
    Argument,
    ChoiceArgument,
    Command,
    FlagArgument,
    Menu,
    Shortcut,
    ValueArgument,
)

TABLE_CONFIG = dict(
    show_header=False, box=None, title_justify="left", title_style=Style(italic=True)
)
TABLE_PADDING = (1, 0, 1, 0)
DIM_STYLE = Style(dim=True)
ENABLED_STYLE = Style(color="green", italic=True)
HIGHLIGHT_STYLE = Style(color="green", bold=True)


def should_dim(key: str, user_input: str) -> str:
    return not key.startswith(user_input)


def render_command(command: Command) -> str:
    return [command.name, command.description]


def render_value(value: str | None) -> str:
    if value is None:
        return ""
    elif value == "":  # special case for a valid empty string input
        return '""'
    else:
        return value


def render_argument(argument: Argument) -> str:
    match argument:
        case FlagArgument():
            return [argument.flag, argument.description]
        case ChoiceArgument():
            choices_str = " | ".join(argument.choices)
            choices_str = f"[ {choices_str} ]"
            if argument.selected:
                choices_str = Text(choices_str)
                choices_str.highlight_words([f" {argument.selected} "], HIGHLIGHT_STYLE)
            return [
                Text.assemble(argument.name, "=", argument.selected or ""),
                Text.assemble(argument.description, " ", choices_str),
            ]
        case ValueArgument():
            return [
                f"{argument.name}={render_value(argument.value)}",
                argument.description,
            ]
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


def group_arguments(
    arguments: List[Argument],
) -> DefaultDict[str, List[Tuple[Shortcut, Argument]]]:
    default_group = "Arguments"
    groups = defaultdict(list)

    for key, argument in arguments.items():
        groups[argument.group or default_group].append((key, argument))

    return groups


def render_arguments_group(
    group_name: str, arguments: List[Tuple[Shortcut, Argument]], user_input: str
):
    table = Table(
        "key", "name", Column("desc", max_width=80), title=group_name, **TABLE_CONFIG
    )
    for key, argument in arguments:
        style = None
        if argument.enabled:
            style = ENABLED_STYLE
        elif should_dim(key, user_input):
            style = DIM_STYLE

        key = render_key(key, user_input)
        table.add_row(key, *render_argument(argument), style=style)
    return Padding(table, TABLE_PADDING)


def render_menu(menu: Menu, user_input: str):
    yield Text(menu.name, style="bold")
    if menu.menus:
        table = Table("key", "prefix", title="Subcommands", **TABLE_CONFIG)
        for key, prefix in menu.menus.items():
            table.add_row(key, prefix.name)
        yield Padding(table, TABLE_PADDING)

    if menu.arguments:
        groups = group_arguments(menu.arguments)
        for group_name, arguments in groups.items():
            yield render_arguments_group(group_name, arguments, user_input)

    if menu.commands:
        table = Table(
            "key",
            "name",
            Column("desc", max_width=80),
            title="Commands",
            **TABLE_CONFIG,
        )
        for key, command in menu.commands.items():
            log(f"Render command {key}: {command}")
            table.add_row(key, *render_command(command))
        yield Padding(table, TABLE_PADDING)
