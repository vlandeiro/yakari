import pkgutil
import subprocess
import sys
from typing import Callable
from uuid import uuid4
from pathlib import Path
import click
import structlog
from rich.table import Table
from textual import events, log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid
from textual.message import Message, MessageTarget
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, TextLog
from textual import log

from .action import Action, Argument
from .models import Transient, Argument, Command, Flag
from .config import Config
from .state_machine import StateMachine

# log = structlog.get_logger()


class InputValueSetter(Screen):
    def __init__(self, on_success, on_empty, *args, **kwargs):
        self.on_success = on_success
        self.on_empty = on_empty
        placeholder = kwargs.pop("placeholder", "value")
        self.accept_null_value = kwargs.pop("accept_null_value", True)
        self.user_input = Input(id="user-input", placeholder=placeholder)
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield self.user_input

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            if not self.user_input.value and not self.accept_null_value:
                return

            if self.user_input.value:
                self.on_success(self.user_input.value)
            else:
                self.on_empty(self.user_input.value)

            event.stop()
            self.app.pop_screen()

        elif event.key == "ctrl+g":
            event.stop()
            self.app.pop_screen()


class TransientKeymapWidget(Widget):
    transient = reactive(Transient.empty())
    input_buffer = reactive("")
    stack = []

    def argument_value_setter(
            self,
            argument: Argument,
            placeholder="value",
            accept_null_value=True,
            send_command=False
    ):

        def on_success(new_value):
            argument.value = new_value
            argument.is_active = True

        def on_empty(new_value):
            argument.value = ""
            argument.is_active = False

        input_screen = InputValueSetter(
            on_success=on_success,
            on_empty=on_empty,
            placeholder=placeholder,
            accept_null_value=accept_null_value
        )

        self.app.push_screen(input_screen)
        input_screen.user_input.focus()

    def on_key(self, event: events.Key) -> None:
        key, char = event.key, event.char

        self.transient.highlighted_keys = set()

        # Backtrack to the previous state
        if key == "ctrl+g":
            if len(self.stack):
                log("Tracking back")
                self.transient = self.stack.pop(-1)
                self.input_buffer = ""
            else:
                self.app.exit()
            return

        if not char:
            return

        self.input_buffer += char

        # Handle matching user input
        if self.input_buffer in self.transient.keymap:
            target = self.transient.keymap[self.input_buffer]

            if isinstance(target, Transient):
                self.stack.append(self.transient)
                self.transient = target

            elif isinstance(target, Flag):
                target.is_active = not target.is_active

            elif isinstance(target, Argument):
                self.argument_value_setter(target)

            elif isinstance(target, Command):
                send_command = True
                for parameter in target.parameters:
                    if not parameter.is_optional and not parameter.param.is_active:
                        self.transient.highlighted_keys.add(parameter.param.key)
                        send_command = False

                if send_command:
                    self.app.exit(target.to_list())

            self.input_buffer = ""
            self.transient.disabled_keys = set()

            log(self.transient.highlighted_keys)
        else:
            # Disable keys that don't match the input buffer
            for key in self.transient.keymap:
                if key in self.transient.disabled_keys:
                    continue
                if not key.startswith(self.input_buffer):
                    self.transient.disabled_keys.add(key)

            # Reset input buffer and disabled keys when no remaining keys match the
            # user input
            if set(self.transient.keymap) == self.transient.disabled_keys:
                self.transient.disabled_keys = set()
                self.input_buffer = ""

    def render(self):
        return self.transient


class PyTransientApp(App):
    CSS_PATH = "vertical_layout.css"

    BINDINGS = [
        Binding(
            key="ctrl+g",
            key_display="CTRL+G",
            action="do_nothing_1",
            description="Go back / Exit",
        ),
    ]

    def __init__(self, transient, *args, **kwargs):
        self.transient = transient
        super().__init__(*args, **kwargs)

    def on_key(self, event):
        self.transient_widget.on_key(event)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.transient_widget = TransientKeymapWidget()
        self.transient_widget.transient = self.transient

        yield self.transient_widget
        yield Footer()
