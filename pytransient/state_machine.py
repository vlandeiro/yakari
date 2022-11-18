import json
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

import structlog
from attrs import asdict, define, field
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table

from .action import Action, Argument, Flag, NamedArgument
from .config import Config
from .constants import *

log = structlog.get_logger()


@define
class StateMachine:
    stack: List[Action] = field(repr=lambda x: [action.name for action in x])
    transitions: Dict[str, Argument] = field(
        repr=lambda x: {src: x[src].name for src in x.keys()}
    )
    value_setter: Callable
    input_buffer: str = ""

    @classmethod
    def empty(cls):
        return cls([], dict(), lambda arg: None, "")

    @classmethod
    def from_action(cls, action: Action, value_setter: Callable):
        transitions = cls._get_transitions_from_action(action)
        action.toggle()
        stack = [action]
        return cls(stack=stack, transitions=transitions, value_setter=value_setter)

    def apply(self, key: str, char: str):
        log.debug(f"Received transition key={key}, char={char}")
        if not char:
            return

        # Backtrack to the previous state
        if key == "ctrl+g":
            self.input_buffer = ""
            # backtrack until we reach the end of user-inputted commands
            if len(self.stack) > 1:
                discarded_state = self.stack.pop(-1)
                discarded_state.toggle()
                self._populate_transitions()
            return

        self.input_buffer += char

        # Final sequence handling
        if key == "enter":
            log.info(self.stack[0].generate_command())

        # Handle matching input
        if self.input_buffer in self.transitions:
            self._goto(self.transitions[self.input_buffer])
            self._reset_input_buffer()
            return

        # Handle invalid input
        if not any(k.startswith(self.input_buffer) for k in self.transitions.keys()):
            self._reset_input_buffer()
            return

    def _goto(self, new_state: Argument):
        # Toggle the flag and stay in the same state
        if isinstance(new_state, Flag):
            new_state.toggle()

        # Pass argument to a value setter that takes care of updating the
        # argument value and toggle it if it's active.
        elif isinstance(new_state, NamedArgument):
            self.value_setter(new_state)

        # Move to the selected action
        elif isinstance(new_state, Action):
            self.stack.append(new_state)
            self._populate_transitions()
            new_state.toggle()

    def _populate_transitions(self):
        self.transitions = self._get_transitions_from_action(self.stack[-1])

    @staticmethod
    def _get_transitions_from_action(action: Action):
        return {arg.key: arg for arg in action.arguments}

    def _reset_input_buffer(self):
        log.debug("Resetting input buffer.")
        self.input_buffer = ""

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(show_header=False, box=None)

        table.add_column("Key", justify="left", style="cyan")
        table.add_column("Name")
        table.add_column("Rendered", style="dim")
        table.add_column("Help")
        table.add_column("Value", style="emphasize")

        action = self.stack[-1]
        for arg in action.arguments:
            style = None
            if arg.is_active:
                style = "bold"

            arg_value = None
            if hasattr(arg, "value"):
                arg_value = arg.value

            arg_name = arg.name
            if isinstance(arg, NamedArgument):
                arg_name = f"{arg.name}="
            arg_rendered = None
            if arg.rendered:
                arg_rendered = f"({arg.rendered})"
            table.add_row(
                arg.key, arg_name, arg_rendered, arg.help_msg, arg_value, style=style
            )

        yield table

    def generate_command(self):
        return self.stack[0].generate_command()


if __name__ == "__main__":
    config = Config.from_toml("./configurations/git.toml")
    action = config.actions["git"]

    def uuid_setter(arg):
        from uuid import uuid4

        arg.value = str(uuid4())

    state_machine = StateMachine.from_action(action, uuid_setter)

    # start from git state
    # transitions are [c] checkout, [s] status, or [C] clone
    print(state_machine)
    state_machine.apply(None, "c")
    print(state_machine)
    # state is checkout
    # transitions are [-b] branch, [-q] quiet
    print(state_machine)
    state_machine.apply(None, "-")  # branch
    state_machine.apply(None, "b")  # branch
    print(state_machine)
    # state is branch
    # user inputs name of the branch
    # branch name is saved
    # state is checkout
    print(state_machine)
    state_machine.apply(None, "-t")  # branch
    print(state_machine)
    print(state_machine)
    state_machine.apply(None, "-t")  # branch
    print(state_machine)
    print(state_machine)
    state_machine.apply("enter", "return")  # finalize
    print(state_machine)
    # command is generated using BFS from start state, traversing active transitions
    log.info(asdict(config))
