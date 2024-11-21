"""
A module for defining menu structure and commands using Pydantic models.
This module provides classes to represent actions, commands, command groups,
and complete menu structures in a type-safe way.
"""

import os
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Self

import tomlkit
from pydantic import BaseModel, Field, PrivateAttr


class Deferred(BaseModel):
    varname: str

    def evaluate(self, context=None):
        context = context or globals()
        return context[self.varname]


class History(BaseModel):
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
    exact_match: str | None = None
    partial_matches: List[str] = Field(default_factory=list)


Shortcut = str


class Argument(BaseModel):
    template: str | None = Field(
        default=None,
        description=(
            "A templated python string to represent the argument. "
            "It can attributes available on `self`."
        ),
    )
    description: str = Field(
        default="", description="A short description for the argument."
    )
    group: str | None = Field(
        default=None, description="The name of the group this argument belongs to."
    )

    def render_template(self) -> str:
        return self.template.format(self=self)


class FlagArgument(Argument):
    flag: str
    template: str = "{self.flag}"
    on: bool = Field(
        default=False, description="State of the flag argument, True when enabled."
    )

    @property
    def enabled(self):
        return self.on


class ChoiceArgument(Argument):
    name: str
    choices: List[str] = Field(
        description="A list of available values for this argument."
    )
    selected: str | None = Field(
        default=None,
        description="The selection value for this argument. MUST be one of the values in `choices`.",
    )
    template: str = "{self.name} {self.selected}"

    @property
    def enabled(self):
        return self.selected is not None

    # TODO: add validation that `selected` is one of the values in `choices`


class ValueArgument(Argument):
    name: str
    value: str | None = Field(default=None, description="The value for this argument.")
    _history: List[str] = PrivateAttr(default_factory=History)

    @property
    def enabled(self):
        return self.value is not None

    def add_to_history(self, value: str | None):
        self._history.add(value)

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


class Command(BaseModel):
    """
    Represents a command with an associated shortcut and action.

    Attributes:
        template (str): The templated command to execute when this action runs
    """

    name: str
    description: str = ""
    template: List[str | Deferred | ArgumentImpl]


class Menu(BaseModel):
    """
    Represents the complete menu structure containing groups of commands.

    Attributes:
        name (str): The name of the menu
        commands (List[Command]): A list of commands belonging to this group
    """

    name: str
    arguments: Dict[Shortcut, ArgumentImpl] = Field(default_factory=dict)
    menus: Dict[Shortcut, "Menu"] = Field(default_factory=dict)
    commands: Dict[Shortcut, Command] = Field(default_factory=dict)

    _ancestors_arguments: Dict[Shortcut, Argument] = PrivateAttr(default_factory=dict)

    @classmethod
    def from_toml(cls, command_name: str) -> Self:
        base_path = Path(os.environ.get("HOME")) / ".config" / "yakari"
        config_path = (base_path / command_name).with_suffix(".toml")

        if not (config_path.exists() and config_path.is_file()):
            raise ValueError(f"No configuration file for command '{command_name}'.")

        with config_path.open("r") as fd:
            model = tomlkit.load(fd).unwrap()
        return cls.model_validate(model)
