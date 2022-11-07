from typing import Optional, List, Any, Dict, Type, Union, Callable
from enum import Enum
from .constants import *
import json
from attrs import define, field
import structlog

log = structlog.get_logger()

@define(slots=False)
class Argument:
    name: str
    key: str
    is_active: bool
    help_msg: str
    rendered: Optional[str]

    @classmethod
    def from_dict(cls, name: str, arguments: Dict) -> Type["Argument"]:
        kind = arguments.pop(KIND)
        if kind not in VALID_KINDS:
            raise ValueError(
                f"Entry with name {name} must have a {KIND} field associated with one "
                f"of {VALID_KINDS} as a value. You provided {KIND}={kind}."
            )

        name = arguments.pop(NAME, name)
        try:
            key = arguments.pop(KEY)
        except KeyError:
            raise ValueError(
                f"Entry with name {name} must have a field named '{KEY}'."
            )
        rendered = arguments.pop(RENDERED_NAME, None)

        common_kwargs = dict(
            name=name,
            key=key,
            is_active=False,
            help_msg="",
            rendered=rendered,
        )

        if kind == ArgumentType.ACTION:
            parsed_arguments = []
            for arg_name, arg in arguments.items():
                parsed_arg = Argument.from_dict(arg_name, arg)
                parsed_arguments.append(parsed_arg)

            return Action(**common_kwargs, arguments=parsed_arguments)

        elif kind == ArgumentType.POSITIONAL:
            return NamedArgument(**common_kwargs, is_positional=True)

        elif kind == ArgumentType.NAMED:
            return NamedArgument(**common_kwargs, is_positional=False)

        elif kind == ArgumentType.FLAG:
            return Flag(**common_kwargs)

    def toggle(self, value: Optional[bool]=None):
        log.debug(f"Toggled {self.__class__.__name__} {self.name}")
        if value is not None:
            self.is_active = self.value
        else:
            self.is_active = not self.is_active


@define(slots=False)
class Action(Argument):
    arguments: Optional[List[Union["Argument", "Action"]]]

    def generate_command(self):
        active_arguments = [arg for arg in self.arguments if arg.is_active]
        rendered_arguments = " ".join([arg.generate_command() for arg in active_arguments])
        rendered_name = self.rendered or self.name
        return f"{rendered_name} {rendered_arguments}"

@define(slots=False)
class NamedArgument(Argument):
    is_positional: bool
    value: Optional[str] = None

    def generate_command(self) -> str:
        if self.is_positional:
            return self.value
        else:
            rendered_key = self.rendered or self.key
            return f"{rendered_key}={self.value}"

@define(slots=False)
class Flag(Argument):
    def generate_command(self) -> str:
        rendered_key = self.rendered or self.key
        return rendered_key
