from .config import Config
from .action import Argument, Action
from .state_machine import StateMachine
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TextLog, Input, Button
from textual.widget import Widget
from rich.table import Table
from textual import events
from textual.reactive import reactive
from textual.screen import Screen
from uuid import uuid4
from textual.containers import Grid
from textual.message import Message, MessageTarget


class InputScreen(Screen):
    def __init__(self, argument, *args, **kwargs):
        self.argument = argument
        self.user_input = Input(id="footer")
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield self.user_input

    def on_key(self, event: events.Key):
        if event.key == "enter":
            self.argument.value = self.user_input.value
            self.argument.toggle(True)
            self.app.pop_screen()

        elif event.key in {"ctrl+g", "escape"}:
            event.stop()
            self.app.pop_screen()

class CLIConfigWidget(Widget):
    def __init__(self, action: Action, value_setter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state_machine = StateMachine.from_action(action, value_setter)

    def on_key(self, event: events.Key) -> None:
        key, char = event.key, event.char
        self.state_machine.apply(key, char)
        self.state_machine = self.state_machine

    def render(self):
        return self.state_machine

class UI(App):
    CSS_PATH = "vertical_layout.css"

    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.cmd = config.actions["git"]

    def on_key(self, event: events.Key) -> None:
        log = self.query_one(TextLog)
        log.write(event)
        w = self.query_one(CLIConfigWidget)
        w.on_key(event)
        w.refresh()
        log.write(f"State machine: {w.state_machine}")
        log.write(f"Command: {w.state_machine.stack[0].generate_command()}")
        try:
            user_input = self.query_one(InputScreen)
            log.write(f"Input value: {user_input}")
        except:
            pass

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        def value_setter(arg):
            input_screen = InputScreen(arg, id="footer")
            self.push_screen(input_screen)
            input_screen.user_input.focus()

        yield CLIConfigWidget(self.cmd, value_setter)
        yield TextLog(id="sidebar")

if __name__ == "__main__":
    config = Config.from_toml("./configurations/git.toml")
    app = UI(config)
    app.run()
