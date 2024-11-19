from textual import events, log, work
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Input, OptionList, Label
from textual.containers import Container
from textual.containers import Horizontal
from .configurations.uv import main_menu as uv_menu
from .types import (
    Menu,
    Prefix,
    Argument,
    Command,
    FlagArgument,
    ChoiceArgument,
    ValueArgument,
)
import subprocess
from textual.reactive import reactive
from .rich_render import render_prefix, render_menu
import sys


class ChoiceArgumentInputScreen(ModalScreen[int | None]):
    def __init__(self, argument: ValueArgument, *args, **kwargs):
        self.argument = argument
        self.widget = OptionList(*argument.choices)
        super().__init__()

    def compose(self) -> ComposeResult:
        yield self.widget

    def on_key(self, event: events.Key) -> None:
        match event.key:
            case "enter":
                self.dismiss(self.widget.highlighted)
            case "ctrl+g":
                self.dismiss(None)


class ValueArgumentInputScreen(ModalScreen[str | None]):
    def __init__(self, argument: ValueArgument, *args, **kwargs):
        self.argument = argument
        self.argument._history.restart()
        self.label_widget = Label(f"{self.argument.name}=")
        self.input_widget = Input(value="")
        super().__init__()

    def compose(self) -> ComposeResult:
        # yield self.input_widget
        yield Horizontal(self.label_widget, self.input_widget)

    def on_key(self, event: events.Key) -> None:
        match event.key:
            case "enter":
                self.dismiss(self.input_widget.value)
            case "ctrl+g":
                if self.input_widget.value:
                    self.input_widget.value = ""
                    self.argument._history.restart()
                else:
                    self.dismiss(None)
            case "down":
                if (prev_value := self.argument._history.prev) and (
                    prev_value is not None
                ):
                    self.input_widget.value = prev_value
            case "up":
                if (next_value := self.argument._history.next) and (
                    next_value is not None
                ):
                    self.input_widget.value = next_value


class MenuScreen(Screen):
    def __init__(self, menu: Menu):
        super().__init__(classes="main-screen")
        self.menu = menu

    def compose(self) -> ComposeResult:
        for renderable in render_menu(self.menu):
            yield Static(renderable)

    def on_key(self, event: events.Key) -> None:
        if event.key in self.menu.prefixes.keys():
            prefix = self.menu.prefixes[event.key]
            self.app.push_screen(prefix.name)
        elif event.key == "ctrl+g":
            self.app.exit()


class PrefixScreen(Screen):
    cur_input = reactive("", recompose=True)

    def __init__(self, prefix: Prefix):
        super().__init__(classes="main-screen")
        self.prefix = prefix

    def compose(self) -> ComposeResult:
        for renderable in render_prefix(self.prefix, self.cur_input):
            yield Static(renderable)

    @work
    async def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+g":
            if self.cur_input:
                self.cur_input = ""
            else:
                self.app.pop_screen()

        elif event.is_printable:
            new_input = self.cur_input + event.character

            # If we have an exact argument match, then enable it
            if self.string_matches_argument(new_input, exact=True):
                await self.process_argument(self.prefix.arguments[new_input])
                return

            # If we have an exact command match, then execute it
            if self.string_matches_command(new_input, exact=True):
                await self.process_command(self.prefix.commands[new_input])
                self.cur_input = ""
                return

            # If we have partial argument matches, then we update the current
            # input with the new character
            if self.string_matches_argument(new_input):
                self.cur_input = new_input

            # otherwise, we reset the current input
            else:
                self.cur_input = ""

    async def process_argument(self, argument: Argument):
        match argument:
            case FlagArgument():
                argument.value = not argument.value
                self.cur_input = ""
            case ChoiceArgument():

                def set_argument_value_and_reset_input(value: int | None):
                    if value is None:
                        argument.selected = None
                    else:
                        argument.selected = argument.choices[value]
                    self.cur_input = ""

                if argument.selected:
                    set_argument_value_and_reset_input(None)
                else:
                    new_value = await self.app.push_screen_wait(
                        ChoiceArgumentInputScreen(argument),
                    )
                    set_argument_value_and_reset_input(new_value)
            case ValueArgument():

                def set_argument_value_and_reset_input(value: str):
                    argument.value = value
                    argument.add_to_history(value)
                    self.cur_input = ""

                if argument.value is not None:
                    set_argument_value_and_reset_input(None)
                else:
                    new_value = await self.app.push_screen_wait(
                        ValueArgumentInputScreen(argument),
                    )
                    set_argument_value_and_reset_input(new_value)

    async def process_command(self, command: Command):
        resolved_arguments_list = []
        for key, argument in self.prefix.arguments.items():
            if not argument.enabled:
                continue
            resolved_arguments_list.append(argument.render_template())
        resolved_arguments = " ".join(resolved_arguments_list)

        dynamic_arguments_list = []
        for argument in command.dynamic_arguments:
            await self.process_argument(argument)
            dynamic_arguments_list.append(argument.render_template())
        dynamic_arguments = " ".join(dynamic_arguments_list)

        command_template_str = " ".join(command.template)
        command_str = command_template_str.format(
            resolved_arguments=resolved_arguments, dynamic_arguments=dynamic_arguments
        )
        self.app.command = command_str
        self.app.exit()

    def string_matches_argument(self, s: str, exact: bool = False) -> bool:
        candidates = set(self.prefix.arguments.keys())
        log(f"MATCHING: {s} vs {candidates} with exact={exact}")
        if exact:
            return s in candidates
        else:
            return any(key.startswith(s) for key in self.prefix.arguments.keys())

    def string_matches_command(self, s: str, exact: bool = False) -> bool:
        candidates = set(self.prefix.commands.keys())
        if exact:
            return s in candidates
        else:
            return any(key.startswith(s) for key in self.prefix.commands.keys())


class PyTransientApp(App):
    CSS_PATH = "app.css"

    def __init__(self, menu, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.menu = menu
        self.command = None

    def on_mount(self) -> None:
        for key, prefix in self.menu.prefixes.items():
            log(f"Mounting screen for key {key}: {prefix.name}")
            self.install_screen(PrefixScreen(prefix), prefix.name)
            self.push_screen(prefix.name)

        menu_screen = MenuScreen(self.menu)
        self.install_screen(menu_screen, self.menu.name)
        self.push_screen(self.menu.name)

    def on_unmount(self):
        if self.command is not None:
            print(self.command, file=sys.__stdout__, flush=True)


app = PyTransientApp(uv_menu)
