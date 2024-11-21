from textual import events, log, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Label, OptionList, Static

from .configurations._base import Deferred
from .rich_render import render_menu
from .types import (
    Argument,
    ChoiceArgument,
    Command,
    FlagArgument,
    MatchResult,
    Menu,
    ValueArgument,
)


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
                event.stop()


class ValueArgumentInputScreen(ModalScreen[str | None]):
    def __init__(self, argument: ValueArgument, *args, **kwargs):
        self.argument = argument
        self.argument._history.restart()
        self.label_widget = Label(f"{self.argument.name}=")
        self.input_widget = Input(value="")
        super().__init__()

    def compose(self) -> ComposeResult:
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
                    event.stop()
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
    BINDINGS = [
        ("ctrl+g", "reset_or_pop", "Reset input / Go back"),
        ("tab", "complete_input", "Autocomplete"),
        ("backspace", "backspace_input", "Erase last character"),
    ]

    cur_input = reactive("", recompose=True)

    def __init__(self, menu: Menu, is_entrypoint: bool = False):
        super().__init__(classes="main-screen")
        self.menu = menu
        self.is_entrypoint = is_entrypoint
        self.candidates = {**menu.arguments, **menu.menus, **menu.commands}

    def compose(self) -> ComposeResult:
        for renderable in render_menu(self.menu, self.cur_input):
            yield Static(renderable)

    def action_reset_or_pop(self):
        if self.cur_input:
            self.cur_input = ""
        elif self.is_entrypoint:
            self.app.exit()
        else:
            self.app.pop_screen()

    def action_backspace_input(self):
        if self.cur_input:
            self.cur_input = self.cur_input[:-1]

    @work
    async def action_complete_input(self):
        # If we have only one remaining matching argument and we hit tab,
        # complete the current input and process the argument
        match_results = self.string_matches_candidates(self.cur_input)

        if len(match_results.partial_matches) == 1:
            self.cur_input = match_results.partial_matches[0]
            await self.process_match(self.candidates[self.cur_input])

    @work
    async def on_key(self, event: events.Key) -> None:
        if event.is_printable:
            new_input = self.cur_input + event.character

            match_results = self.string_matches_candidates(new_input)

            # If we have an exact match, then process it
            if match_results.exact_match is not None:
                await self.process_match(self.candidates[new_input])

            # If we have partial matches, then we update the current
            # input with the new character
            elif match_results.partial_matches:
                self.cur_input = new_input

            # otherwise, we reset the current input
            else:
                self.cur_input = ""

    async def process_match(self, match_value: Argument | Command | Menu):
        match match_value:
            case Argument():
                await self.process_argument(match_value)
            case Command():
                command_result = await self.process_command(match_value)
                if command_result is None:
                    return
            case Menu():
                await self.process_menu(match_value)

    async def process_argument(self, argument: Argument):
        match argument:
            case FlagArgument():
                argument.on = not argument.on
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
        optional_arguments = []
        all_arguments = {**self.menu._ancestors_arguments, **self.menu.arguments}
        for key, argument in all_arguments.items():
            if argument.enabled:
                optional_arguments.append(argument.render_template())

        resolved_command = []
        for part in command.template:
            match part:
                case str():
                    resolved_command.append(part)
                case Argument():
                    await self.process_argument(part)
                    if not part.enabled:
                        return
                    resolved_command.append(part.render_template())
                case Deferred():
                    resolved_command.extend(part.evaluate(locals()))

        command_str = " ".join(resolved_command)

        self.app.command = command_str
        self.app.exit(resolved_command)

    async def process_menu(self, menu: Menu):
        menu._ancestors_arguments = self.menu.arguments
        await self.app.push_screen_wait(MenuScreen(menu))
        self.cur_input = ""

    def string_matches_candidates(self, s: str) -> MatchResult:
        candidates_set = set(self.candidates)
        exact_match = None
        partial_matches = []
        if s in candidates_set:
            exact_match = s
        else:
            partial_matches = [key for key in candidates_set if key.startswith(s)]
        return MatchResult(exact_match=exact_match, partial_matches=partial_matches)


class YakariApp(App):
    CSS_PATH = "app.css"

    BINDINGS = [
        ("ctrl+g", "quit", "Exit"),
    ]

    def __init__(self, command_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.menu = Menu.from_toml(command_name)
        self.command = None

    def on_mount(self) -> None:
        menu_screen = MenuScreen(self.menu, is_entrypoint=True)
        log(f"Menu: {self.menu}")
        self.install_screen(menu_screen, self.menu.name)
        self.push_screen(self.menu.name)


app = YakariApp("uv")
