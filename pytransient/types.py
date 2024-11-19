"""
A module for defining menu structure and commands using Pydantic models.
This module provides classes to represent actions, commands, command groups,
and complete menu structures in a type-safe way.
"""

from textual import log
from pydantic import BaseModel, Field, PrivateAttr
from typing import Dict, List, Type, Deque
from collections import deque

from typing_extensions import Self

Shortcut = str


class Argument(BaseModel):
    name: str
    template: str
    visible: bool = True
    description: str = ""

    def render_template(self) -> str:
        return self.template.format(self=self)


class FlagArgument(Argument):
    template: str = "{self.name}"
    value: bool = False

    @property
    def enabled(self):
        return self.value


class ChoiceArgument(Argument):
    choices: List[str]
    selected: str | None = None

    @property
    def enabled(self):
        return self.selected is not None


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
        log(f"END RESTART: {self.cur_pos}")

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
        log(f"END PREV: {self.cur_pos} {self.values}")
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
        log(f"END NEXT: {self.cur_pos} {self.values}")
        return self.values[self.cur_pos]


class ValueArgument(Argument):
    template: str = "{self.value}"
    value_type: Type
    value: str | None = None
    _history: List[str] = PrivateAttr(default_factory=History)

    @property
    def enabled(self):
        return self.value is not None

    def add_to_history(self, value: str | None):
        self._history.add(value)


class Command(BaseModel):
    """
    Represents a command with an associated shortcut and action.

    Attributes:
        template (str): The templated command to execute when this action runs
    """

    name: str
    description: str = ""
    template: List[str]
    dynamic_arguments: List[Argument] = Field(default_factory=list)


class Prefix(BaseModel):
    name: str
    arguments: Dict[Shortcut, Argument]
    commands: Dict[Shortcut, Command]


class Menu(BaseModel):
    """
    Represents the complete menu structure containing groups of commands.

    Attributes:
        name (str): The name of the menu
        commands (List[Command]): A list of commands belonging to this group
    """

    name: str
    prefixes: Dict[Shortcut, Prefix]
