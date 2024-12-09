import shelve
import subprocess
from collections import deque
from pathlib import Path
from typing import List, Literal

from rich.text import Text
from rich.rule import Rule
from rich.syntax import Syntax
from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.suggester import SuggestFromList
from textual.widgets import (
    Input,
    Label,
    OptionList,
    RichLog,
    SelectionList,
    Static,
)
from textual.widget import Widget
from textual.message import Message

from . import constants as C
from .rich_render import render_menu, ERROR_STYLE
from .types import (
    Argument,
    ChoiceArgument,
    Command,
    MenuArguments,
    FlagArgument,
    History,
    MatchResult,
    Menu,
    ValueArgument,
)


class ChoiceArgumentInputScreen(ModalScreen[int | List[str] | None]):
    """A modal screen for selecting from a list of choices for an argument.

    Args:
        argument (ValueArgument): The argument containing the choices
    """

    def __init__(self, argument: ChoiceArgument):
        self.argument = argument
        if self.argument.multi:
            selected = set()
            if self.argument.selected:
                selected = set(argument.selected)
            selections = [
                (choice, choice, True) if choice in selected else (choice, choice)
                for choice in argument.choices
            ]
            self.widget = SelectionList(*selections)
            self.result_attr = "selected"
        else:
            self.widget = OptionList(*argument.choices)
            self.result_attr = "highlighted"
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical():
            yield self.widget

    def on_key(self, event: events.Key) -> None:
        result = getattr(self.widget, self.result_attr)
        match event.key:
            case "enter":
                self.dismiss(result)
            case "ctrl+g":
                self.dismiss(None)
                event.stop()


class ArgumentInput(Widget):
    result: reactive[list[str]] = reactive(list, recompose=True)
    highlighted: reactive[int] = reactive(int, recompose=True)

    class Submitted(Message):
        def __init__(self, value: List[str] | str) -> None:
            self.value = value
            super().__init__()

    def __init__(self, argument: Argument, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.argument = argument
        self.with_history = not argument.password

        self.label_widget = Label(f"{self.argument.name}=")

        suggester = None
        if argument.suggestions:
            suggester = SuggestFromList(argument.suggestions.values)
        self.input_widget = Input(password=argument.password, suggester=suggester)

        if argument.multi and argument.value and isinstance(argument.value, list):
            self.result = argument.value
            self.highlighted = len(self.result) - 1
            self.mutate_reactive(ArgumentInput.result)
        elif argument.value:
            self.input_widget.value = argument.value

    def on_mount(self):
        if self.with_history:
            self.shelf = shelve.open(C.HISTORY_FILE, writeback=True)
            self.history = History(values=self.shelf.get(self.argument.name, deque()))

    def on_unmount(self):
        if self.with_history:
            self.shelf[self.argument.name] = self.history.values
            self.shelf.close()

    def set_text(self, value: str):
        self.input_widget.value = value

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Horizontal(self.label_widget, self.input_widget, id="labelled-input")
            if self.argument.multi:
                parts = []
                for idx, r in enumerate(self.result):
                    classes = (
                        "result highlighted" if idx == self.highlighted else "result"
                    )
                    parts.append(Label(r, classes=classes))
                parts.append(self.input_widget)
                yield Horizontal(*parts, classes="highlights")

    def focus(self, *args, **kwargs):
        self.input_widget.focus(*args, **kwargs)

    def on_key(self, event: events.Key) -> None:
        match event.key:
            case "enter":
                if self.input_widget.value and self.with_history:
                    self.history.add(self.input_widget.value)

                if self.argument.multi:
                    if not self.input_widget.value:
                        self.post_message(self.Submitted(self.result))
                    else:
                        self.result.append(self.input_widget.value)
                        self.highlighted = len(self.result) - 1
                        self.mutate_reactive(ArgumentInput.result)
                        self.input_widget.value = ""
                        self.input_widget.focus()
                else:
                    self.post_message(self.Submitted(self.input_widget.value))
                event.stop()

            case "ctrl+g":
                if self.input_widget.value:
                    self.input_widget.value = ""
                    if self.with_history:
                        self.history.restart()
                else:
                    self.post_message(self.Submitted(None))
                event.stop()

            case "down":
                if (
                    self.with_history
                    and (prev_value := self.history.prev)
                    and (prev_value is not None)
                ):
                    self.input_widget.value = prev_value

            case "up":
                if (
                    self.with_history
                    and (next_value := self.history.next)
                    and (next_value is not None)
                ):
                    self.input_widget.value = next_value

            case "left":
                if not self.input_widget.value and self.result:
                    self.highlighted = max(0, self.highlighted - 1)
                    self.input_widget.focus()

            case "right":
                if not self.input_widget.value and self.result:
                    self.highlighted = min(len(self.result) - 1, self.highlighted + 1)
                    self.input_widget.focus()

            case "backspace":
                if not self.input_widget.value and self.result:
                    self.result.pop(self.highlighted)
                    self.highlighted = 0
                    self.mutate_reactive(ArgumentInput.result)
                    self.input_widget.focus()


class SuggestionsList(Widget):
    class SuggestionSelected(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    def __init__(self, suggested_values: List[str]):
        super().__init__()
        self.suggested_values = suggested_values

        self.suggestions_widget = OptionList(
            *self.suggested_values,
            id="suggestions",
        )
        self.suggestions_widget.border_title = "Suggested values"

    def compose(self) -> ComposeResult:
        yield self.suggestions_widget

    def on_option_list_option_selected(self, message: OptionList.OptionSelected):
        self.post_message(
            self.SuggestionSelected(self.suggested_values[message.option_index])
        )


class ValueArgumentInputScreen(ModalScreen[str | None]):
    """A modal screen for entering a value for an argument.

    Args:
        argument (ValueArgument): The argument to get input for
    """

    def __init__(self, argument: ValueArgument):
        super().__init__()
        self.argument = argument
        self.input_widget = ArgumentInput(argument)
        self.suggestions_widget = None
        if self.argument.suggestions:
            self.suggestions_widget = SuggestionsList(self.argument.suggestions.values)

    def _init_suggestions(self):
        self.suggester = None
        self.suggested_values = None
        self.suggestions_widget = None

        if self.argument.suggestions:
            self.suggested_values = self.argument.suggestions.values
            self.suggester = SuggestFromList(self.suggested_values)
            self.suggestions_widget = self._make_suggestions_widget()

    def compose(self) -> ComposeResult:
        with Vertical():
            if self.suggestions_widget is not None:
                yield self.suggestions_widget
            yield self.input_widget

    def on_mount(self):
        self.input_widget.focus()

    def on_key(self, event: events.Key):
        match event.key:
            case "ctrl+g":
                self.dismiss(None)
                event.stop()

    def on_argument_input_submitted(self, message: ArgumentInput.Submitted):
        self.dismiss(message.value)

    def on_suggestions_list_suggestion_selected(
        self, message: SuggestionsList.SuggestionSelected
    ):
        self.input_widget.set_text(message.value)
        self.input_widget.focus()
        message.stop()


class ResultScreen(ModalScreen):
    BINDINGS = [
        ("q", "pop_screen", "Quit"),
        ("ctrl+g", "pop_screen", "Quit"),
        ("slash", "pop_screen", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.log_widget = RichLog(highlight=True, wrap=True)

    def compose(self) -> ComposeResult:
        yield self.log_widget

    def action_pop_screen(self):
        self.app.pop_screen()


class MenuScreen(Screen):
    """Main screen showing the menu interface and handling user input.

    Attributes:
        cur_input (reactive): Current user input string
    """

    BINDINGS = [
        ("ctrl+g", "reset_or_pop", "Reset / Back"),
        ("slash", "show_results", "Show Results"),
        ("tab", "complete_input", "Complete"),
        ("backspace", "backspace_input", "Erase"),
        ("ctrl+e", "change_mode", "Toggle mode"),
    ]

    cur_input = reactive("", recompose=True)
    edit_mode = reactive(False, recompose=True)

    def __init__(
        self, menu: Menu, is_entrypoint: bool = False, ancestor_input: str = ""
    ):
        super().__init__()
        self.menu = menu
        self.is_entrypoint = is_entrypoint
        self.ancestor_input = ancestor_input
        self.candidates = {**menu.arguments, **menu.menus, **menu.commands}

    def compose(self) -> ComposeResult:
        for renderable in render_menu(self.menu, self.cur_input):
            yield Static(renderable)

        cur_input_display = Horizontal(
            Label(self._get_full_input()),
            id="cur-input",
        )

        shortcut_description = dict()
        if self.app.inplace:
            shortcut_description["/"] = "toggle results"
        shortcut_description["backspace"] = "erase 1"
        shortcut_description["ctrl+g"] = "reset / go back"
        shortcut_description["ctrl+e"] = "toggle edit mode"
        shortcut_description["ctrl+c"] = "quit"

        labels = [Label("Shortcuts:", classes="title")]
        for shortcut, description in shortcut_description.items():
            labels.append(Label(f"({shortcut})", classes="help"))
            labels.append(Label(description))
        help_display = Horizontal(*labels, id="help-section")

        is_edit_mode = "yes" if self.edit_mode else "no"
        mode_display = Horizontal(
            Label("Edit mode:", classes="title"), Label(is_edit_mode), id="mode"
        )

        yield Horizontal(cur_input_display, help_display, mode_display, id="footer")

    def action_show_results(self):
        if self.app.inplace:
            self.app.push_screen("results")

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
            self.dismiss(None)

    def action_backspace_input(self):
        """Remove the last character from current input."""
        if self.cur_input:
            self.cur_input = self.cur_input[:-1]

    def action_change_mode(self):
        self.edit_mode = not self.edit_mode

    def _get_full_input(self) -> str:
        full_input = self.cur_input
        if self.ancestor_input:
            full_input = f"{self.ancestor_input} >> {self.cur_input}"
        return full_input

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
                self.cur_input = new_input
                await self.process_match(self.candidates[new_input])
                event.stop()

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
                await self.process_argument(
                    match_value, action="edit" if self.edit_mode else "toggle"
                )
            case Command():
                command = await self.process_command(match_value)
                if command is None:
                    return

            case Menu():
                await self.process_menu(match_value)

    async def process_argument(
        self, argument: Argument, action: Literal["edit"] | Literal["toggle"] = "toggle"
    ):
        """Handle processing of different argument types.

        Args:
            argument (Argument): The argument to process
            action (Literal["edit"] | Literal["toggle"]): Whether the targeted argument should be edited or
            toggled when active. This parameter has no effect for `FlagArgument` instances.

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

                def set_argument_value_and_reset_input(value: int | List[str] | None):
                    if value is None:
                        argument.selected = None
                    elif isinstance(value, int):
                        argument.selected = [argument.choices[value]]
                    else:
                        argument.selected = value
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
                    self.cur_input = ""

                if argument.value is not None and action == "toggle":
                    set_argument_value_and_reset_input(None)
                else:
                    new_value = await self.app.push_screen_wait(
                        ValueArgumentInputScreen(argument),
                    )
                    set_argument_value_and_reset_input(new_value)

    async def process_command(self, command: Command):
        """Process a command by resolving its template and arguments.

        Args:
            command (Command): The command to process

        Resolves the command template with argument values and exits app
        with the final command.
        """
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
                case MenuArguments():
                    arguments = part.resolve_arguments(self.menu)
                    for key, argument in arguments.items():
                        if argument.enabled:
                            rendered_argument = argument.render_template()
                            match rendered_argument:
                                case str():
                                    resolved_command.append(rendered_argument)
                                case list():
                                    resolved_command.extend(rendered_argument)

        self.app.command = resolved_command
        self.cur_input = ""

        logw: RichLog = self.app.results_screen.log_widget
        command_str = " ".join(resolved_command)
        logw.write(Text(f"$> {command_str}"))

        if self.app.inplace:
            self.app.push_screen("results")

        if self.app.dry_run:
            if not self.app.inplace:
                self.app.exit()
        else:
            if self.app.inplace:
                result = subprocess.run(resolved_command, capture_output=True)
                if result.stderr:
                    logw.write(Text(result.stderr.decode(), style=ERROR_STYLE))
                if result.stdout:
                    logw.write(
                        Syntax(
                            result.stdout.decode(),
                            command.lexer or "bash",
                            indent_guides=True,
                            word_wrap=True,
                            padding=1,
                        ),
                        scroll_end=True,
                    )
            else:
                self.app.exit(resolved_command)

    async def process_menu(self, menu: Menu):
        """Process a submenu by pushing a new menu screen.

        Args:
            menu (Menu): The submenu to display
        """
        menu._ancestors_arguments = self.menu.arguments
        await self.app.push_screen_wait(
            MenuScreen(menu, ancestor_input=self._get_full_input())
        )
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

    CSS_PATH = "app.css"
    COMMAND_PALETTE_BINDING = "question_mark"
    BINDINGS = [
        ("ctrl+g", "quit", "Exit"),
    ]

    def __init__(
        self,
        command_or_menu: str | Path | Menu,
        dry_run: bool = False,
        inplace: bool = False,
    ):
        super().__init__()
        self.command = None
        self.dry_run = dry_run
        self.inplace = inplace

        match command_or_menu:
            case Menu():
                self.menu = command_or_menu
            case _:
                self.menu = Menu.from_toml(command_or_menu)
        self.menu_screen = MenuScreen(self.menu, is_entrypoint=True)
        self.results_screen = ResultScreen()

    def on_mount(self) -> None:
        self.install_screen(self.results_screen, "results")
        self.install_screen(self.menu_screen, self.menu.name)
        self.push_screen(self.menu.name)
