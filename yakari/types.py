"""
A module for defining menu structure and commands using Pydantic models.
This module provides classes to represent actions, commands, command groups,
and complete menu structures in a type-safe way using Pydantic data validation.
"""

import subprocess
from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Literal, Self

import tomlkit
from pydantic import BaseModel, Field, PrivateAttr, model_validator

from . import constants as C


class Deferred(BaseModel):
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


class Argument(BaseModel):
    """
    Base class for all command arguments, providing common functionality.

    Attributes:
        template (str | List[str] | None): A templated python string to render the argument.
        description (str): A short description explaining the argument's purpose.
        group (str | None): The name of the group this argument belongs to.
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


class NamedArgument(Argument, ABC):
    name: str
    separator: Literal["space"] | Literal["equal"] = C.DEFAULT_ARGUMENT_FIELDS["separator"]
    multi: bool = False
    multi_style: Literal["repeat"] | str = C.DEFAULT_ARGUMENT_FIELDS["multi_style"]

    @property
    def positional(self):
        return not self.name.startswith("-")

    @abstractmethod
    def get_value_list(self) -> List[str]:
        raise NotImplementedError()

    def render_template(self) -> List[str] | str:
        if self.template is not None:
            return super().render_template()

        values = self.get_value_list()
        if self.positional:
            multi_style = " " if self.multi_style == "repeat" else self.multi_style
            return multi_style.join(values)

        if not self.multi:
            value = values[0]
            match self.separator:
                case "space":
                    return [self.name, value]
                case "equal":
                    return f"{self.name}={value}"

        if self.multi_style == "repeat":
            result = []
            for value in values:
                match self.separator:
                    case "space":
                        result.extend([self.name, value])
                    case "equal":
                        result.append(f"{self.name}={value}")
            return result

        match self.separator:
            case "space":
                return [self.name, self.multi_style.join(values)]
            case "equal":
                return f"{self.name}={self.multi_style.join(values)}"


class ChoiceArgument(NamedArgument):
    """
    Represents a command argument that must be chosen from a predefined set of values.

    Attributes:
        name (str): Name of the argument
        choices (List[str]): Available values to choose from
        selected (str | None): Currently selected value
    """

    choices: List[str] = Field(
        description="A list of available values for this argument."
    )
    selected: List[str] | None = Field(
        default=None,
        description="The selection value for this argument.",
    )

    @property
    def enabled(self):
        return self.selected is not None

    def get_value_list(self):
        if self.selected is None:
            return None
        return self.selected


class SuggestionsList(BaseModel):
    values: List[str]


class SuggestionsCommand(BaseModel):
    command: str
    disable_caching: bool = False
    _suggestions: List[str] = PrivateAttr(default_factory=list)

    @property
    def values(self):
        if self.disable_caching or not self._suggestions:
            result = subprocess.run(self.command, capture_output=True, shell=True)
            if result.stderr:
                raise RuntimeError(
                    f"Command {self.command} failed with the following "
                    f"message:\n{result.stderr.decode()}"
                )
            self._suggestions = [
                line.strip()
                for line in result.stdout.decode().split("\n")
                if line.strip()
            ]
        return self._suggestions


SuggestionsImpl = SuggestionsList | SuggestionsCommand


class ValueArgument(NamedArgument):
    """
    Represents a command argument that accepts an arbitrary value.

    Attributes:
        name (str): Name of the argument. Should
        value (str | None): The argument's value
        password (bool): True if the argument represents a field that should be obfuscated.
                         Defaults to False.
    """

    value: str | List[str] | None = Field(
        default=None, description="The value for this argument."
    )
    password: bool = False
    suggestions: SuggestionsImpl | None = None

    @property
    def enabled(self):
        return self.value is not None

    def get_value_list(self):
        if self.value is None:
            return None
        if isinstance(self.value, str):
            return [self.value]
        return self.value


ArgumentImpl = FlagArgument | ValueArgument | ChoiceArgument


class Command(BaseModel):
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


class MenuConfiguration(BaseModel):
    separator: Literal["space"] | Literal["equal"] = C.DEFAULT_ARGUMENT_FIELDS["separator"]
    multi_style: Literal["repeat"] | str = C.DEFAULT_ARGUMENT_FIELDS["multi_style"]


class Menu(BaseModel):
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
    configuration: MenuConfiguration = Field(default_factory=MenuConfiguration)

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
                f"No configuration found for '{command_name}'."
            )

        with config_path.open("r") as fd:
            model = tomlkit.load(fd).unwrap()
        return cls.model_validate(model)

    @model_validator(mode="after")
    def set_default_fields(self) -> Self:
        config_fields_set = self.configuration.model_fields_set

        for arg in self.arguments.values():
            arg_fields = arg.model_fields
            arg_fields_set = arg.model_fields_set
            for field_name in config_fields_set:
                if field_name in arg_fields and field_name not in arg_fields_set:
                    default_value = getattr(self.configuration, field_name)
                    setattr(arg, field_name, default_value)

        for menu in self.menus.values():
            menu.configuration = self.configuration
            menu.set_default_fields()

        return self
