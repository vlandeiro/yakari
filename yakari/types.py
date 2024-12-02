"""
A module for defining menu structure and commands using Pydantic models.
This module provides classes to represent actions, commands, command groups,
and complete menu structures in a type-safe way using Pydantic data validation.
"""

from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Self
from uuid import uuid4

import tomlkit
from pydantic import BaseModel, Field, PrivateAttr

from . import constants as C


class YakariType(BaseModel):
    _id: str = PrivateAttr(default_factory=lambda: str(uuid4()))


class Deferred(YakariType):
    """A class representing a deferred value that will be evaluated at runtime from a variable."""

    varname: str

    def evaluate(self, context: Dict[str, Any]):
        return context[self.varname]


class History(BaseModel):
    """A class managing command history with navigation capabilities."""

    values: Deque[str] = Field(default_factory=deque)
    cur_pos: int | None = None

    def add(self, value: str):
        if not value:
            return
        if not self.values or (self.values and self.values[0] != value):
            self.values.appendleft(value)

    def restart(self):
        if not self.values:
            self.cur_pos = None
            return
        self.cur_pos = -1

    @property
    def current(self) -> str | None:
        if self.cur_pos is None:
            return None
        return self.values[self.cur_pos]

    @property
    def prev(self) -> str | None:
        if self.cur_pos is None:
            return None
        prev_index = self.cur_pos + 1
        if prev_index >= len(self.values):
            self.cur_pos = 0
        else:
            self.cur_pos = prev_index
        return self.values[self.cur_pos]

    @property
    def next(self) -> str | None:
        if self.cur_pos is None:
            return None
        next_index = self.cur_pos - 1
        if next_index < 0:
            self.cur_pos = len(self.values) - 1
        else:
            self.cur_pos = next_index
        return self.values[self.cur_pos]


class MatchResult(BaseModel):
    """
    Represents the result of a command/argument matching operation.

    Attributes:
        exact_match (str | None): The exact match found, if any
        partial_matches (List[str]): List of partial matches found
    """

    exact_match: str | None = None
    partial_matches: List[str] = Field(default_factory=list)


class Argument(YakariType):
    """
    Base class for all command arguments, providing common functionality.

    Attributes:
        template (str | List[str] | None): A templated python string to render the argument.
        description (str): A short description explaining the argument's purpose
        group (str | None): The name of the group this argument belongs to
    """

    template: str | List[str] | None = Field(
        default=None,
        description=(
            "A templated python string to represent the argument. "
            "It can use attributes available on `self`."
        ),
    )
    description: str = Field(
        default="", description="A short description for the argument."
    )
    group: str | None = Field(
        default=None, description="The name of the group this argument belongs to."
    )

    def render_template(self) -> List[str] | str:
        match self.template:
            case list():
                return [part.format(self=self) for part in self.template]
            case str():
                return self.template.format(self=self)
            case _:
                return


class FlagArgument(Argument):
    """
    Represents a flag-style command argument that can be enabled or disabled.

    Attributes:
        flag (str): The flag string (e.g. '--verbose')
        on (bool): Whether the flag is enabled
    """

    flag: str
    template: str = "{self.flag}"
    on: bool = Field(
        default=False, description="State of the flag argument, True when enabled."
    )

    @property
    def enabled(self):
        return self.on


class ChoiceArgument(Argument):
    """
    Represents a command argument that must be chosen from a predefined set of values.

    Attributes:
        name (str): Name of the argument
        choices (List[str]): Available values to choose from
        selected (str | None): Currently selected value
    """

    name: str
    choices: List[str] = Field(
        description="A list of available values for this argument."
    )
    selected: str | List[str] | None = Field(
        default=None,
        description="The selection value for this argument.",
    )
    template: str = "{self.name} {self.selected}"

    @property
    def enabled(self):
        return self.selected is not None


class ValueArgument(Argument):
    """
    Represents a command argument that accepts an arbitrary value.

    Attributes:
        name (str): Name of the argument. Should
        value (str | None): The argument's value
        password (bool): True if the argument represents a field that should be obfuscated.
                         Defaults to False.
    """

    name: str
    value: str | None = Field(default=None, description="The value for this argument.")
    password: bool = False

    @property
    def enabled(self):
        return self.value is not None

    @property
    def positional(self):
        return not self.name.startswith("-")

    def render_template(self):
        if self.template is not None:
            return super().render_template()
        elif self.positional:
            return f"{self.value}"
        else:
            return f"{self.name} {self.value}"


# TODO: add multi-value argument


ArgumentImpl = FlagArgument | ValueArgument | ChoiceArgument


class Command(YakariType):
    """
    Represents a command with configurable arguments and template-based execution.

    Attributes:
        name (str): Unique identifier/name for the command
        description (str): Optional description explaining the command's purpose
        template (List[str | Deferred | ArgumentImpl]): List of components that make up the
            command, can include raw strings, deferred values, and various argument types
    """

    name: str
    description: str = ""
    template: List[str | Deferred | ArgumentImpl]


Shortcut = str


class Menu(YakariType):
    """
    Represents the complete menu structure containing groups of commands.

    Attributes:
        name (str): The name of the menu
        arguments (Dict[Shortcut, ArgumentImpl]): Available arguments mapped by shortcuts
        menus (Dict[Shortcut, Menu]): Sub-menus mapped by shortcuts
        commands (Dict[Shortcut, Command]): Available commands mapped by shortcuts
    """

    name: str
    arguments: Dict[Shortcut, ArgumentImpl] = Field(default_factory=dict)
    menus: Dict[Shortcut, Self] = Field(default_factory=dict)
    commands: Dict[Shortcut, Command] = Field(default_factory=dict)

    _ancestors_arguments: Dict[Shortcut, Argument] = PrivateAttr(default_factory=dict)

    @classmethod
    def from_toml(cls, command_name: str | Path) -> Self:
        if isinstance(command_name, Path):
            config_path = command_name
        else:
            base_path = C.YAKARI_HOME / C.CONFIGURATIONS_DIR
            config_path = (base_path / command_name).with_suffix(".toml")

        if not (config_path.exists() and config_path.is_file()):
            raise ValueError(
                f"No configuration file for command '{command_name}' in {base_path}."
            )

        with config_path.open("r") as fd:
            model = tomlkit.load(fd).unwrap()
        return cls.model_validate(model)
