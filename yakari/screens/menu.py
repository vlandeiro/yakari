from typing import List, Literal

from rich.text import Text
from textual import events, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Static,
)

from ..rich_render import render_menu
from ..types import (
    Argument,
    ChoiceArgument,
    Command,
    CommandTemplateResolver,
    FlagArgument,
    MatchResult,
    Menu,
    ValueArgument,
)
from ..widgets import Footer, CommandRunner
from .choice_argument import ChoiceArgumentInputScreen
from .value_argument import ValueArgumentInputScreen


class MenuScreen(Screen):
    """Main screen showing the menu interface and handling user input.

    Attributes:
        cur_input (reactive): Current user input string
    """

    BINDINGS = [
        Binding("backspace", "backspace_input", "erase / go back"),
        Binding("tab", "complete_input", "complete", show=False),
        Binding("ctrl+e", "change_mode", "toggle edit mode"),
        Binding("ctrl+r", "show_results", "show results"),
    ]

    cur_input = reactive("", recompose=True)
    edit_mode = reactive(False, recompose=True)

    def __init__(self, menu: Menu, is_entrypoint: bool = False):
        super().__init__()
        self.menu = menu
        self.is_entrypoint = is_entrypoint
        self.candidates = {**menu.arguments, **menu.menus, **menu.commands}

    def compose(self) -> ComposeResult:
        for renderable in render_menu(self.menu, self.cur_input):
            yield Static(renderable)
        yield Footer()

    @work
    async def action_show_results(self):
        if self.app.inplace:
            await self.app.push_screen_wait("results")
            self.refresh_bindings()

    def action_backspace_input(self):
        """Remove the last character from current input."""
        if self.cur_input:
            self.cur_input = self.cur_input[:-1]
        elif not self.is_entrypoint:
            self.dismiss(None)

    def action_change_mode(self):
        self.edit_mode = not self.edit_mode

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

                def set_argument_value_and_reset_input(value: str | List[str] | None):
                    if value is None:
                        argument.selected = None
                    elif isinstance(value, str):
                        argument.selected = [value]
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

        async def process_argument_fn(argument: Argument):
            return await self.process_argument(argument, action="edit")

        template_resolver = CommandTemplateResolver(
            process_argument_fn=process_argument_fn
        )
        self.app.command = await template_resolver.resolve(self.menu, command.template)
        self.cur_input = ""

        if self.app.command is None:
            return

        results_widget: CommandRunner = self.app.results_screen.cmd_runner
        command_str = " ".join(self.app.command)

        inplace = command.inplace if command.inplace is not None else self.app.inplace

        if self.app.dry_run:
            if inplace:
                self.app.push_screen("results")
                results_widget.write(Text(f"$> {command_str}"))
            if not inplace:
                self.app.exit(result=None, return_code=0, message=command_str)

        else:
            if inplace:
                self.app.push_screen("results")
                results_widget.start_subprocess(self.app.command)
            else:
                self.app.exit(
                    result=self.app.command, return_code=0, message=command_str
                )

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
