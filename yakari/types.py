"""
A module for defining menu structure and commands using Pydantic models.
This module provides classes to represent actions, commands, command groups,
and complete menu structures in a type-safe way using Pydantic data validation.
"""

import subprocess
import urllib
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Literal, Self

import tomlkit
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from . import constants as C


Shortcut = str


class YakariType(BaseModel):
    model_config = ConfigDict(extra="forbid")


class History(YakariType):
    """A class managing command history with navigation capabilities."""

    values: Dict[str, int] = Field(default_factory=dict)
    max_size: int = 20
    _cur_pos: int | None = PrivateAttr(default=None)

    def add(self, value: str):
        if not value:
            return

        if value in self.values:
            del self.values[value]
        self.values[value] = 1

        if len(self.values) > self.max_size:
            first_key = list(self.values.keys())[0]
            del self.values[first_key]


class MatchResult(YakariType):
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
    separator: Literal["space"] | Literal["equal"] = C.DEFAULT_ARGUMENT_FIELDS[
        "separator"
    ]
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
            if self.multi_style == "repeat":
                return values
            else:
                return self.multi_style.join(values)

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
    selected: str | List[str] | None = Field(
        default=None,
        description="The selection value for this argument.",
    )

    @property
    def enabled(self):
        return self.selected is not None

    def get_value_list(self):
        if self.selected is None:
            return None
        elif isinstance(self.selected, str):
            return [self.selected]
        return self.selected

    @model_validator(mode="after")
    def sanitize_selected_value(self):
        if isinstance(self.selected, str):
            self.selected = [self.selected]
        return self


class SuggestionsList(YakariType):
    values: List[str]


class SuggestionsCommand(YakariType):
    command: str
    cache: bool = False
    _suggestions: List[str] = PrivateAttr(default_factory=list)

    @property
    def values(self):
        if not self.cache or not self._suggestions:
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


class MenuArguments(YakariType):
    include: Literal["*"] | List[str]
    exclude: List[str] | None = None
    scope: Literal["this"] | Literal["all"] = "all"

    def resolve_arguments(self, menu: "Menu") -> Dict[Shortcut, Argument]:
        arguments = dict()
        if self.scope == "all":
            arguments.update(menu._ancestors_arguments)
        arguments.update(menu.arguments)

        if self.include != "*":
            arguments = {
                shortcut: arg
                for shortcut, arg in arguments.items()
                if shortcut in self.include
            }
        if self.exclude:
            arguments = {
                shortcut: arg
                for shortcut, arg in arguments.items()
                if shortcut not in self.exclude
            }

        return arguments


CommandTemplate = List[str | MenuArguments | ArgumentImpl]


class Command(YakariType):
    """
    Represents a command with configurable arguments and template-based execution.

    Attributes:
        name (str): Unique identifier/name for the command
        description (str): Optional description explaining the command's purpose
        template (List[str | MenuArguments | ArgumentImpl]): List of components that make up the
            command, can include raw strings, deferred values, and various argument types
    """

    name: str
    description: str = ""
    template: CommandTemplate
    inplace: bool | None = None


class NamedArgumentsStyle(YakariType):
    separator: Literal["space"] | Literal["equal"] = C.DEFAULT_ARGUMENT_FIELDS[
        "separator"
    ]
    multi_style: Literal["repeat"] | str = C.DEFAULT_ARGUMENT_FIELDS["multi_style"]


class MenuConfiguration(YakariType):
    named_arguments_style: NamedArgumentsStyle = Field(
        default_factory=NamedArgumentsStyle
    )
    sort_arguments: bool = True
    sort_commands: bool = True
    sort_menus: bool = True


def set_default_arg_value(arg: Argument, configuration: MenuConfiguration):
    config_fields_set = configuration.named_arguments_style.model_fields_set
    arg_fields = arg.model_fields
    arg_fields_set = arg.model_fields_set
    for field_name in config_fields_set:
        if field_name in arg_fields and field_name not in arg_fields_set:
            default_value = getattr(configuration.named_arguments_style, field_name)
            setattr(arg, field_name, default_value)
    return arg


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
    configuration: MenuConfiguration = Field(default_factory=MenuConfiguration)

    _ancestors_arguments: Dict[Shortcut, Argument] = PrivateAttr(default_factory=dict)

    @classmethod
    def from_toml(cls, command_name: str | Path) -> Self:
        if isinstance(command_name, Path):  # local path
            config_path = command_name

        elif command_name.startswith(("http://", "https://")):  # url
            # resolve the URL to a local path
            url = command_name
            parsed_url = urllib.parse.urlparse(url)
            filename = urllib.parse.unquote(Path(parsed_url.path).name)
            config_path = C.YAKARI_HOME / C.TEMPORARY_MENUS_DIR / filename
            config_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, config_path)

        else:  # command name
            base_path = C.YAKARI_HOME / C.MENUS_DIR
            config_path = (base_path / command_name).with_suffix(".toml")

        if not (
            config_path.exists() and config_path.is_file()
        ):  # no local configuration exists
            try:
                # try to retrieve an online configuration
                return cls.from_toml(f"{C.REMOTE_DEFAULT}/{command_name}.toml")
            except Exception:
                raise ValueError(f"No configuration found for '{command_name}'.")

        with config_path.open("r") as fd:
            model = tomlkit.load(fd).unwrap()
        return cls.model_validate(model)

    @model_validator(mode="after")
    def set_default_fields(self) -> Self:
        # propagate defaults to menu arguments
        for arg in self.arguments.values():
            set_default_arg_value(arg, self.configuration)

        # propagate defaults to dynamic arguments in commands
        for command in self.commands.values():
            for part in command.template:
                if isinstance(part, Argument):
                    set_default_arg_value(part, self.configuration)

        # propagate the parent menu configuration to all child menus unless it
        # was explicitly set
        for menu in self.menus.values():
            menu_fields_set = menu.model_fields_set
            if "configuration" not in menu_fields_set:
                menu.configuration = self.configuration
            menu.set_default_fields()

        return self


class CommandTemplateResolver(YakariType):
    process_argument_fn: Callable[[Argument], Awaitable[None]]
    resolved_command: List[str] = Field(default_factory=list)

    async def resolve(self, menu: Menu, template: CommandTemplate) -> List[str] | None:
        resolved_command = []

        def update_resolved_command(rendered_argument: str | List[str]) -> List[str]:
            match rendered_argument:
                case str():
                    resolved_command.append(rendered_argument)
                case list():
                    resolved_command.extend(rendered_argument)

        for part in template:
            match part:
                case str():
                    resolved_command.append(part)

                case Argument():
                    argument = part
                    await self.process_argument_fn(argument)
                    if argument.enabled:
                        update_resolved_command(argument.render_template())
                    else:
                        return None
                case MenuArguments():
                    arguments = part.resolve_arguments(menu)
                    for key, argument in arguments.items():
                        if argument.enabled:
                            update_resolved_command(argument.render_template())

        return resolved_command
