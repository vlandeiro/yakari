from collections import defaultdict
from typing import DefaultDict, List, Tuple

from rich.padding import Padding
from rich.style import Style
from rich.table import Column, Table
from rich.text import Text

from .types import (
    Argument,
    ChoiceArgument,
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
ERROR_STYLE = Style(color="red")


def should_dim(key: str, user_input: str) -> str:
    """
    Determine if a key should be dimmed based on user input.

    Args:
        key: The key to check
        user_input: The current user input string

    Returns:
        bool: True if the key should be dimmed, False otherwise
    """
    return not key.startswith(user_input)


def render_value(value: str | None, obfuscate: bool = False) -> str:
    """
    Convert a value to its string representation for display.

    Args:
        value: The value to render, can be None or a string

    Returns:
        str: The rendered string representation of the value:
            - Empty string for None
            - Quoted empty string for ""
            - Original value otherwise
    """
    if value is None:
        return ""
    elif value == "":  # special case for a valid empty string input
        return '""'
    elif obfuscate:
        return "*" * min(len(value), 40)
    elif len(value) > 40:
        return f"{value[:18]}...{value[-18:]}"
    else:
        return str(value)


def render_argument(argument: Argument) -> Tuple[str | Text, str | Text]:
    """
    Render an argument into a displayable format.

    Args:
        argument: The Argument object to render (FlagArgument, ChoiceArgument, or ValueArgument)

    Returns:
        Tuple[str | Text, str | Text]: A tuple containing:
            - The rendered argument name/value
            - The rendered description with optional formatting

    Raises:
        ValueError: If the argument type is not supported
    """
    match argument:
        case FlagArgument():
            return (argument.flag, argument.description)
        case ChoiceArgument():
            choices_str = " | ".join(argument.choices)
            choices_str = f"[ {choices_str} ]"
            choices_str = Text(choices_str)
            if argument.selected:
                choices_str.highlight_words(
                    [f" {value} " for value in argument.selected], HIGHLIGHT_STYLE
                )
            arg_value = argument.selected
            if not argument.multi and argument.selected:
                arg_value = argument.selected[0]
            return (
                Text.assemble(argument.name, "=", render_value(arg_value)),
                Text.assemble(argument.description, " ", choices_str),
            )
        case ValueArgument():
            return (
                f"{argument.name}={render_value(argument.value, obfuscate=argument.password)}",
                argument.description,
            )
        case _:
            raise ValueError(f"{argument} of type {type(argument)} is not supported.")


def render_key(key: str, user_input: str) -> Text:
    """
    Render a key with optional styling.

    Args:
        key (str): The key to render
        user_input: The current user input string

    Returns:
        Union[Text, str]: Rendered key text with applied style
    """
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
) -> Padding:
    """
    Render a group of arguments as a formatted table with styling based on argument state.

    Args:
        group_name (str): Title of the argument group to be displayed
        arguments (List[Tuple[Shortcut, Argument]]): List of tuples containing shortcuts and their
            corresponding arguments to be rendered
        user_input (str): Current user input string used for determining styling

    Returns:
        Padding: A Rich Padding object containing the formatted table with proper spacing

    Note:
        The table includes columns for key, name, and description with appropriate styling:
        - Enabled arguments use ENABLED_STYLE
        - Dimmed arguments (based on user input) use DIM_STYLE
    """
    table = Table(
        "key", "name", Column("desc", max_width=80), title=group_name, **TABLE_CONFIG
    )
    for key, argument in arguments:
        style = None
        if should_dim(key, user_input):
            style = DIM_STYLE
        elif argument.enabled:
            style = ENABLED_STYLE

        key = render_key(key, user_input)
        table.add_row(key, *render_argument(argument), style=style)
    return Padding(table, TABLE_PADDING)


def render_menu(menu: Menu, user_input: str):
    """
    Generate a complete menu rendering including title, subcommands, arguments, and commands.

    Args:
        menu (Menu): Menu object containing all elements to be rendered
        user_input (str): Current user input string used for styling and filtering
        sort_by_keys (bool): Whether to sort the entries by their keyboard shortcuts. Defaults to True.

    Yields:
        Union[Text, Padding]: A sequence of Rich components representing different parts of the menu:
            - Menu title as Text
            - Subcommands table as Padding (if menu.menus exists)
            - Argument groups as Padding (if menu.arguments exists)
            - Commands table as Padding (if menu.commands exists)

    Note:
        Each section (subcommands, arguments, commands) is rendered in a separate table
        with appropriate formatting and column configurations defined in TABLE_CONFIG
    """
    yield Text(menu.name, style="bold")
    if menu.menus:
        table = Table("key", "prefix", title="Subcommands", **TABLE_CONFIG)
        menu_items = (
            sorted(menu.menus.items(), key=lambda x: x[0].lower())
            if menu.configuration.sort_menus
            else menu.menus.items()
        )
        for key, prefix in menu_items:
            style = None
            if should_dim(key, user_input):
                style = DIM_STYLE
            key = render_key(key, user_input)
            table.add_row(key, prefix.name, style=style)
        yield Padding(table, TABLE_PADDING)

    if menu.arguments:
        groups = group_arguments(menu.arguments)
        for group_name, arguments in groups.items():
            arguments = (
                sorted(arguments, key=lambda x: x[0].lower())
                if menu.configuration.sort_arguments
                else arguments
            )
            yield render_arguments_group(group_name, arguments, user_input)

    if menu.commands:
        table = Table(
            "key",
            "name",
            Column("desc", max_width=80),
            title="Commands",
            **TABLE_CONFIG,
        )
        commands_items = (
            sorted(menu.commands.items(), key=lambda x: x[0].lower())
            if menu.configuration.sort_commands
            else menu.commands.items()
        )
        for key, command in commands_items:
            style = None
            if should_dim(key, user_input):
                style = DIM_STYLE
            key = render_key(key, user_input)
            table.add_row(key, command.name, command.description, style=style)
        yield Padding(table, TABLE_PADDING)
