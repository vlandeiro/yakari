from textual import events, log
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Input, OptionList
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

from textual.reactive import reactive
from .rich_render import render_prefix, render_menu


class ChoiceArgumentInputScreen(ModalScreen[int | None]):
    def __init__(self, argument: ValueArgument, *args, **kwargs):
        self.argument = argument
        self.widget = OptionList(*argument.choices)
        super().__init__()

    def compose(self) -> ComposeResult:
        yield self.widget

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.dismiss(self.widget.highlighted)
        elif event.key == "ctrl+g":
            self.dismiss(None)


class ValueArgumentInputScreen(ModalScreen[str | None]):
    def __init__(self, argument: ValueArgument, *args, **kwargs):
        self.argument = argument
        self.input_widget = Input(
            value=self.argument.value, placeholder=self.argument.name
        )
        super().__init__()

    def compose(self) -> ComposeResult:
        yield self.input_widget

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.dismiss(self.input_widget.value)
        elif event.key == "ctrl+g":
            if self.input_widget.value:
                self.input_widget.value = ""
            else:
                self.dismiss(None)


class MenuScreen(Screen):
    def __init__(self, menu: Menu, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.menu = menu

    def compose(self) -> ComposeResult:
        for renderable in render_menu(self.menu):
            yield Static(renderable)

    def on_key(self, event: events.Key) -> None:
        if event.key in self.menu.prefixes.keys():
            prefix = self.menu.prefixes[event.key]
            self.app.push_screen(prefix.name)


class PrefixScreen(Screen):
    cur_input = reactive("", recompose=True)

    def __init__(self, prefix: Prefix, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix

    def compose(self) -> ComposeResult:
        for renderable in render_prefix(self.prefix, self.cur_input):
            yield Static(renderable)

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+g":
            if self.cur_input:
                self.cur_input = ""
            else:
                self.app.pop_screen()

        elif event.is_printable:
            new_input = self.cur_input + event.character

            # If we have an exact argument match, then enable it
            if self.string_matches_argument(new_input, exact=True):
                self.process_argument(self.prefix.arguments[new_input])
                return

            # If we have an exact command match, then execute it
            if self.string_matches_command(new_input, exact=True):
                self.process_command(self.prefix.commands[new_input])
                self.cur_input = ""
                return

            # If we have partial argument matches, then we update the current
            # input with the new character
            if self.string_matches_argument(new_input):
                self.cur_input = new_input

            # otherwise, we reset the current input
            else:
                self.cur_input = ""

    def process_argument(self, argument: Argument):
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
                    self.app.push_screen(
                        ChoiceArgumentInputScreen(argument),
                        set_argument_value_and_reset_input,
                    )
            case ValueArgument():

                def set_argument_value_and_reset_input(value: str):
                    argument.value = value
                    self.cur_input = ""

                if argument.value is not None:
                    set_argument_value_and_reset_input(None)
                else:
                    self.app.push_screen(
                        ValueArgumentInputScreen(argument),
                        set_argument_value_and_reset_input,
                    )

    def process_command(self, command: Command):
        log(f"RUNNING: {command.template}")

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
    def __init__(self, menu, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.menu = menu

    def on_mount(self) -> None:
        for key, prefix in self.menu.prefixes.items():
            log(f"Mounting screen for key {key}: {prefix.name}")
            self.install_screen(PrefixScreen(prefix), prefix.name)
            self.push_screen(prefix.name)

        menu_screen = MenuScreen(self.menu)
        self.install_screen(menu_screen, self.menu.name)
        self.push_screen(self.menu.name)


app = PyTransientApp(uv_menu)
# app.run()
