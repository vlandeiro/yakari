import pkgutil
import subprocess
import sys
from typing import Callable
from pathlib import Path
from textual import events, log
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Input, Static
from textual import log

from .models import Transient, Argument, Command, Flag


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
    stack = []

    def render(self):
        return self.transient

    def pop(self):
        if len(self.stack):
            self.transient = self.stack.pop(-1)
        else:
            self.app.exit()

    def has_match(self, key):
        return key in self.transient.keymap

    def argument_value_setter(
        self,
        argument: Argument,
        placeholder="value",
        accept_null_value=True,
        send_command=False,
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
            accept_null_value=accept_null_value,
        )

        self.app.push_screen(input_screen)
        input_screen.user_input.focus()

    def apply(self, key):
        target = self.transient.keymap[key]

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

        self.transient.disabled_keys = set()
        log(f"Highlighted keys: {self.transient.highlighted_keys}")

    def disable_impossible_keys(self, input_buffer):
        log(f"Disabling keys without '{input_buffer}' prefix")
        # Disable keys that don't match the input buffer
        for key in self.transient.keymap:
            if key in self.transient.disabled_keys:
                continue
            if not key.startswith(input_buffer):
                self.transient.disabled_keys.add(key)

        log(f"Disabled keys: {self.transient.disabled_keys}")

    def reset_disabled_keys(self):
        log("Resetting disabled keys")
        self.transient.disabled_keys = set()

    def has_possible_keys(self):
        log(f"Keymap: {set(self.transient.keymap)}")
        log(f"Disabled keys: {self.transient.disabled_keys}")
        result = set(self.transient.keymap) != self.transient.disabled_keys
        log(f"Has possible keys: {result}")
        return result


class PyTransientApp(App):
    CSS_PATH = "vertical_layout.css"

    input_buffer = reactive("")
    transient_widget = reactive(TransientKeymapWidget())

    def on_key(self, event: events.Key) -> None:
        key, char = event.key, event.char
        tw: TransientKeymapWidget = self.query_one("#transient")
        tw.transient.highlighted_keys = set()

        # Backtrack to the previous state
        if key == "ctrl+g":
            log(f"Input buffer on ctrl+g: {self.input_buffer}")
            if self.input_buffer:
                tw.reset_disabled_keys()
            else:
                tw.pop()
            self.input_buffer = ""

        elif char:
            self.input_buffer += char

        tw.refresh()

    def watch_input_buffer(self, new_value: str):
        log(f"input_buffer={new_value}")

        tw: TransientKeymapWidget = self.query_one("#transient")
        buf: Static = self.query_one("#buffer")

        buf.update(new_value)
        if not new_value:
            return

        # Handle matching user input
        if tw.has_match(self.input_buffer):
            tw.apply(self.input_buffer)
            self.input_buffer = ""

        else:
            tw.disable_impossible_keys(self.input_buffer)
            if not tw.has_possible_keys():
                tw.reset_disabled_keys()
                self.input_buffer = ""

    def compose(self) -> ComposeResult:
        yield self.transient_widget
        yield Static(id="buffer")


# tw = TransientKeymapWidget(id="transient")
# tw.transient = Transient.from_command_name("git")

# app = PyTransientApp()
# app.transient_widget = tw
# cmd = app.run()
