"""
A module for defining menu structure and commands using Pydantic models.
This module provides classes to represent actions, commands, command groups,
and complete menu structures in a type-safe way.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Tuple, Type


Shortcut = str


class Argument(BaseModel):
    name: str
    template: str
    visible: bool = True
    enabled: bool = False


class FlagArgument(Argument):
    template: str = "{self.name}"


class ChoiceArgument(Argument):
    choices: List[str]
    selected: str | None = None


class ValueArgument(Argument):
    template: str = "{self.value}"
    value_type: Type
    value: str | None = None


class Command(BaseModel):
    """
    Represents a command with an associated shortcut and action.

    Attributes:
        template (str): The templated command to execute when this action runs
    """
    name: str
    template: str
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
