from pathlib import Path
from typing import Literal

from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Label, OptionList, Static

from .rich_render import render_menu
from .types import (
    Argument,
    ChoiceArgument,
    Command,
    Deferred,
    FlagArgument,
    MatchResult,
    Menu,
    ValueArgument,
)


class ChoiceArgumentInputScreen(ModalScreen[int | None]):
    """A modal screen for selecting from a list of choices for an argument.

    Args:
        argument (ValueArgument): The argument containing the choices
    """

    def __init__(self, argument: ValueArgument):
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
    """A modal screen for entering a value for an argument.

    Args:
        argument (ValueArgument): The argument to get input for
    """

    def __init__(self, argument: ValueArgument, value: str = ""):
        self.argument = argument
        self.argument._history.restart()
        self.label_widget = Label(f"{self.argument.name}=")
        self.input_widget = Input(value=value)
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
    """Main screen showing the menu interface and handling user input.

    Attributes:
        cur_input (reactive): Current user input string
    """

    BINDINGS = [
        ("ctrl+g", "reset_or_pop", "Reset input / Go back"),
        ("tab", "complete_input", "Autocomplete"),
        ("backspace", "backspace_input", "Erase last character"),
    ]

    cur_input = reactive("", recompose=True)

    def __init__(self, menu: Menu, is_entrypoint: bool = False):
        super().__init__()
        self.menu = menu
        self.is_entrypoint = is_entrypoint
        self.candidates = {**menu.arguments, **menu.menus, **menu.commands}

    def compose(self) -> ComposeResult:
        yield Label(self.cur_input)
        for renderable in render_menu(self.menu, self.cur_input):
            yield Static(renderable)

    def action_reset_or_pop(self):
        """Reset current input or pop screen if no input.

        If there is current input, clear it. Otherwise, exit app if at entrypoint
        or pop the screen if in a submenu.
        """
        if self.cur_input:
            self.cur_input = ""
        elif self.is_entrypoint:
            self.app.exit()
        else:
            self.app.pop_screen()

    def action_backspace_input(self):
        """Remove the last character from current input."""
        if self.cur_input:
            self.cur_input = self.cur_input[:-1]

    @work
    async def action_complete_input(self):
        """Handle tab completion of current input."""

        # If we have only one remaining matching argument and we hit tab,
        # complete the current input and process the argument
        match_results = self.string_matches_candidates(self.cur_input)

        if len(match_results.partial_matches) == 1:
            self.cur_input = match_results.partial_matches[0]
            await self.process_match(self.candidates[self.cur_input])

    @work
    async def on_key(self, event: events.Key) -> None:
        """Handle key press events.

        Args:
            event (events.Key): The key press event

        Handles printable characters by:
        - Processing exact matches immediately
        - Adding character to input if there are partial matches
        - Resetting input if no matches
        """

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
        """Process a matched menu item based on its type.

        Args:
            match_value: The matched argument, command or submenu
        """
        match match_value:
            case Argument():
                await self.process_argument(match_value)
            case Command():
                command_result = await self.process_command(match_value)
                if command_result is None:
                    return
            case Menu():
                await self.process_menu(match_value)

    async def process_argument(
        self, argument: Argument, action: Literal["edit"] | Literal["toggle"] = "toggle"
    ):
        """Handle processing of different argument types.

        Args:
            argument (Argument): The argument to process
            action (Literal["edit"] | Literal["toggle"]): Whether the targeted argument should be edited or toggled when active. This parameter has no effect for `FlagArgument` instances.

        Handles:
        - Toggling flag arguments
        - Getting choice selection from modal
        - Getting value input from modal
        """
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

                if argument.selected and action == "toggle":
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

                if argument.value is not None and action == "toggle":
                    set_argument_value_and_reset_input(None)
                else:
                    new_value = await self.app.push_screen_wait(
                        ValueArgumentInputScreen(argument, argument.value),
                    )
                    set_argument_value_and_reset_input(new_value)

    async def process_command(self, command: Command):
        """Process a command by resolving its template and arguments.

        Args:
            command (Command): The command to process

        Resolves the command template with argument values and exits app
        with the final command.
        """

        optional_arguments = []
        all_arguments = {**self.menu._ancestors_arguments, **self.menu.arguments}
        for key, argument in all_arguments.items():
            if argument.enabled:
                rendered_argument = argument.render_template()
                match rendered_argument:
                    case str():
                        optional_arguments.append(rendered_argument)
                    case list():
                        optional_arguments.extend(rendered_argument)

        resolved_command = []
        for part in command.template:
            match part:
                case str():
                    resolved_command.append(part)
                case Argument():
                    await self.process_argument(part, action="edit")
                    if not part.enabled:
                        return
                    rendered_argument = part.render_template()
                    match rendered_argument:
                        case str():
                            resolved_command.append(rendered_argument)
                        case list():
                            resolved_command.extend(rendered_argument)
                case Deferred():
                    resolved_command.extend(part.evaluate(locals()))

        self.app.command = resolved_command
        self.app.exit(resolved_command)

    async def process_menu(self, menu: Menu):
        """Process a submenu by pushing a new menu screen.

        Args:
            menu (Menu): The submenu to display
        """

        menu._ancestors_arguments = self.menu.arguments
        await self.app.push_screen_wait(MenuScreen(menu))
        self.cur_input = ""

    def string_matches_candidates(self, s: str) -> MatchResult:
        """Find matches for input string against available options.

        Args:
            s (str): Input string to match

        Returns:
            MatchResult: Contains exact and partial matches found
        """
        candidates_set = set(self.candidates)
        exact_match = None
        partial_matches = []
        if s in candidates_set:
            exact_match = s
        else:
            partial_matches = [key for key in candidates_set if key.startswith(s)]
        return MatchResult(exact_match=exact_match, partial_matches=partial_matches)


class YakariApp(App):
    """Main application class for Yakari command-line interface."""

    ENABLE_COMMAND_PALETTE = False
    CSS_PATH = "app.css"
    BINDINGS = [
        ("ctrl+g", "quit", "Exit"),
    ]

    def __init__(self, command_or_menu: str | Path | Menu):
        super().__init__()
        match command_or_menu:
            case Menu():
                self.menu = command_or_menu
            case _:
                self.menu = Menu.from_toml(command_or_menu)
        self.command = None

    def on_mount(self) -> None:
        menu_screen = MenuScreen(self.menu, is_entrypoint=True)
        self.install_screen(menu_screen, self.menu.name)
        self.push_screen(self.menu.name)
