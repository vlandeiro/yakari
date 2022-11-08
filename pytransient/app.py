import pkgutil
import subprocess
import sys
from typing import Callable
from uuid import uuid4

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

from .action import Action, Argument
from .config import Config
from .state_machine import StateMachine

log = structlog.get_logger()


class InputScreen(Screen):
    def __init__(self, argument, *args, **kwargs):
        self.argument = argument
        self.user_input = Input(id="user-input", placeholder="value")
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield self.user_input

    def on_key(self, event: events.Key):
        if event.key == "enter":
            self.argument.value = self.user_input.value
            self.argument.toggle(True)
            event.stop()
            self.app.pop_screen()

        elif event.key == "ctrl+g":
            event.stop()
            self.app.pop_screen()


class CLIConfigWidget(Widget):
    def __init__(self, action: Action, value_setter: Callable, *args, **kwargs):
        self.state_machine = StateMachine.from_action(action, value_setter)
        super().__init__(*args, **kwargs)

    def on_key(self, event: events.Key) -> None:
        self.state_machine.apply(event.key, event.char)

    def generate_command(self) -> str:
        return self.state_machine.generate_command()

    def render(self):
        return self.state_machine


class PyTransientApp(App):
    CSS_PATH = "vertical_layout.css"

    BINDINGS = [
        Binding(
            key="ctrl+g",
            key_display="CTRL+G",
            action="do_nothing_1",
            description="Go back",
        ),
        Binding(
            key="enter",
            key_display="ENTER",
            action="do_nothing_2",
            description="Run the command",
        ),
    ]

    def __init__(self, command, *args, **kwargs):
        self.command: Action = command
        super().__init__(*args, **kwargs)

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            cmd = self.config_widget.generate_command()
            self.app.action_quit()
            self.app.exit(cmd)

        self.config_widget.on_key(event)
        self.config_widget.refresh()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        def value_setter(arg):
            input_screen = InputScreen(arg)
            self.push_screen(input_screen)
            input_screen.user_input.focus()

        self.config_widget = CLIConfigWidget(
            self.command, value_setter, id="command-selection"
        )

        yield self.config_widget
        yield Footer()
