import asyncio
import shelve
from pathlib import Path
from typing import List, Literal

from rich.text import Text
from textual import events, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.suggester import SuggestFromList
from textual.widgets import (
    Button,
    Input,
    Label,
    OptionList,
    RichLog,
    SelectionList,
    Static,
)
from textual.widget import Widget
from textual.message import Message
from textual.widgets.option_list import Option, Separator

from . import constants as C
from .rich_render import render_menu
from .types import (
    Argument,
    ChoiceArgument,
    Command,
    CommandTemplateResolver,
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
            self.widget = SelectionList(*selections, classes="input-widget")
            self.result_attr = "selected"
        else:
            self.widget = OptionList(*argument.choices, classes="input-widget")
            self.result_attr = "highlighted"
        self.widget.border_title = self.argument.name
        super().__init__(classes="input-screen")

    def compose(self) -> ComposeResult:
        yield self.widget
        yield Footer(self)

    def on_key(self, event: events.Key) -> None:
        result = getattr(self.widget, self.result_attr)
        match event.key:
            case "enter":
                self.dismiss(result)
            case "ctrl+q":
                self.dismiss(None)
                event.stop()


class Tag(Widget):
    can_focus = True
    can_focus_children = False

    value: reactive[str] = reactive(str, recompose=True)

    BINDINGS = [
        ("backspace", "delete_this", "Delete"),
        ("enter", "delete_this", "Delete"),
    ]

    class Deleted(Message):
        def __init__(self, tag):
            super().__init__()
            self.tag = tag

    def __init__(self, value: str):
        super().__init__()
        self.value = value

    def compose(self) -> ComposeResult:
        yield Button("X")
        yield Label(self.value)

    def delete(self):
        self.post_message(Tag.Deleted(self))

    def on_button_pressed(self, event: Button.Pressed):
        self.delete()

    def action_delete_this(self):
        self.delete()


class TagsCollection(Widget):
    can_focus = False
    can_focus_children = True

    tags: reactive[List[Tag]] = reactive(default=list, recompose=True)

    def _sanitize_tag(self, tag: str | Tag) -> Tag:
        if isinstance(tag, str):
            tag = Tag(value=tag)
        return tag

    def __init__(self, tags: List[str | Tag] | None = None):
        super().__init__()
        if self.tags:
            self.tags = [self._sanitize_tag(tag) for tag in tags]
            self.mutate_reactive(TagsCollection.tags)

    def add_tag(self, *tags: str | Tag):
        for tag in tags:
            tag = self._sanitize_tag(tag)
            self.tags.append(tag)
        self.mutate_reactive(TagsCollection.tags)

    def delete_tag(self, tag: str | Tag):
        tag = self._sanitize_tag(tag)
        self.tags.remove(tag)
        self.mutate_reactive(TagsCollection.tags)

    def on_tag_deleted(self, message: Tag.Deleted):
        self.delete_tag(message.tag)

    def compose(self) -> ComposeResult:
        if self.tags:
            scrollable = ScrollableContainer(*self.tags)
            scrollable.can_focus = False
            yield scrollable

    @property
    def values(self):
        return [tag.value for tag in self.tags]


class ArgumentInput(Widget):
    BINDINGS = [("ctrl+q", "cancel", "Cancel")]

    class Submitted(Message):
        def __init__(self, value: List[str] | str) -> None:
            self.value = value
            super().__init__()

    def __init__(
        self,
        argument: Argument,
        suggested_values: List[str] | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.argument = argument
        self.with_history = not argument.password
        self.tags = TagsCollection()

        suggester = None
        if suggested_values:
            suggester = SuggestFromList(list(filter(None, suggested_values)))
        self.input_widget = Input(
            password=argument.password,
            suggester=suggester,
            id="user_input",
            placeholder="value",
        )

        if argument.multi and argument.value and isinstance(argument.value, list):
            self.tags.add_tag(*argument.value)
        elif argument.value:
            self.input_widget.value = argument.value

    def on_mount(self):
        if self.with_history:
            self.shelf = shelve.open(C.HISTORY_FILE, writeback=True)
            self.history = History(values=self.shelf.get(self.argument.name, dict()))

    def on_unmount(self):
        if self.with_history:
            self.shelf[self.argument.name] = self.history.values
            self.shelf.close()

    def set_value(self, value: str):
        self.input_widget.value = value

    def compose(self) -> ComposeResult:
        yield self.input_widget
        if self.argument.multi:
            yield self.tags

    def focus(self, *args, **kwargs):
        self.input_widget.focus(*args, **kwargs)

    def on_input_submitted(self, event: Input.Submitted):
        if self.input_widget.value and self.with_history:
            self.history.add(self.input_widget.value)

        if self.argument.multi:
            if not self.input_widget.value:
                self.post_message(self.Submitted(self.tags.values))
            else:
                self.tags.add_tag(self.input_widget.value)
                self.input_widget.value = ""
                self.input_widget.focus()
        else:
            self.post_message(self.Submitted(self.input_widget.value))
        event.stop()

    def action_cancel(self) -> None:
        self.input_widget.value = ""
        self.post_message(self.Submitted(None))


class SuggestionsWidget(Widget):
    class SuggestionSelected(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    def __init__(self, suggested_values: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suggested_values = list(filter(None, suggested_values))
        fmt_suggested_values = [
            Option(value) if value is not None else Separator()
            for value in suggested_values
        ]

        self.suggestions_widget = OptionList(
            *fmt_suggested_values,
            id="suggestions",
        )
        self.suggestions_widget.border_title = "Suggested values"

    def compose(self) -> ComposeResult:
        yield self.suggestions_widget


class ValueArgumentInputScreen(ModalScreen[str | None]):
    """A modal screen for entering a value for an argument.

    Args:
        argument (ValueArgument): The argument to get input for
    """

    def __init__(self, argument: ValueArgument):
        super().__init__(classes="input-screen")
        self.argument = argument
        self._init_suggestions()
        self.input_widget = ArgumentInput(
            argument, self.suggested_values, classes="input-widget"
        )
        self.input_widget.border_title = argument.name

    def _init_suggestions(self):
        self.suggested_values = []
        self.suggestions_widget = None

        # Load suggestions from history
        if not self.argument.password:
            with shelve.open(C.HISTORY_FILE, writeback=True) as shelf:
                arg_history = shelf.get(self.argument.name, dict())
                self.suggested_values.extend(list(arg_history)[::-1])

        # Load suggestions from hard-coded list, executed command, or other methods
        if self.argument.suggestions:
            if self.suggested_values:
                self.suggested_values.append(None)
            self.suggested_values.extend(self.argument.suggestions.values)

        if self.suggested_values:
            self.suggestions_widget = SuggestionsWidget(
                self.suggested_values, classes="input-widget"
            )

    def on_mount(self):
        self.input_widget.focus()

    def on_key(self, event: events.Key):
        match event.key:
            case "ctrl+q":
                self.dismiss(None)
                event.stop()

    def on_argument_input_submitted(self, message: ArgumentInput.Submitted):
        self.dismiss(message.value)

    def on_option_list_option_selected(self, message: OptionList.OptionSelected):
        value = message.option.prompt
        self.input_widget.set_value(value)
        self.input_widget.focus()
        message.stop()

    def compose(self) -> ComposeResult:
        if self.suggestions_widget is not None:
            yield self.suggestions_widget
        yield self.input_widget
        yield Footer(self)


class CommandResultsWidget(Widget):
    can_focus_children = True

    process_finished: reactive(bool) = reactive(False, recompose=True)

    def __init__(self):
        super().__init__()
        self.log_widget = RichLog(highlight=True, wrap=True, auto_scroll=True)
        self.log_widget.can_focus = False
        self.user_input = Input(placeholder="Interact with your program")
        self.subprocess: asyncio.subprocess.Process | None = None
        self.extra_stdout: bytes = b""
        self.extra_stdout_lock = asyncio.Lock()

    @work
    async def start_subprocess(self, command: List[str]):
        """Start the subprocess and stream its output."""
        self.log_widget.write(Text(f"$> {' '.join(command)}"))
        try:
            # Start the subprocess
            self.process_finished = False
            self.subprocess = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream the subprocess output
            asyncio.create_task(self.stream_stdout(self.subprocess.stdout))
            asyncio.create_task(self.stream_stderr(self.subprocess.stderr))
            asyncio.create_task(self.extra_stdout_watcher())

            # Wait for the process to finish and display the final message once
            return_code = await self.subprocess.wait()

            if not self.process_finished:  # Only show this once
                self.log_widget.write(
                    Text(
                        f"[Command finished ({return_code})]\n",
                        style="red" if return_code else "green",
                    )
                )
                self.process_finished = True

            self.subprocess = None
        except Exception as e:
            self.log_widget.write(Text(f"Error: {e}"))

    async def extra_stdout_watcher(self):
        SLEEP = 0.1

        while self.subprocess is not None:
            async with self.extra_stdout_lock:
                extra_before = self.extra_stdout

            await asyncio.sleep(SLEEP)

            async with self.extra_stdout_lock:
                extra_after = self.extra_stdout
                if extra_before and extra_before == extra_after:
                    self.log_widget.write(Text(self.extra_stdout.decode()))
                    self.extra_stdout = b""

    async def stream_stderr(self, stream):
        while not stream.at_eof():
            payload = await stream.readline()
            self.log_widget.write(Text(payload.decode(), style="red"))

    async def stream_stdout(self, stream):
        """Continuously read lines from the given stream and display them."""
        READSIZE = 2048

        while not stream.at_eof():
            payload = await stream.read(READSIZE)
            payload, *extra = payload.rsplit(b"\n", 1)

            async with self.extra_stdout_lock:
                payload = self.extra_stdout + payload
                self.log_widget.write(Text(payload.decode().strip()))

            if extra:
                async with self.extra_stdout_lock:
                    self.extra_stdout = extra[0]
            else:
                payload = b""
                async with self.extra_stdout_lock:
                    self.extra_stdout = b""

    async def send_input(self, user_input: str):
        """Send user input to the subprocess."""
        if self.subprocess and self.subprocess.stdin:
            self.subprocess.stdin.write(user_input.encode() + b"\n")
            await self.subprocess.stdin.drain()
            self.log_widget.write(f"\nI> {user_input}")

    async def terminate_subprocess(self):
        if self.subprocess:
            self.subprocess.terminate()
            await self.subprocess.wait()

    async def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        user_input = self.user_input.value
        await self.send_input(user_input)
        self.user_input.value = ""

    def write(self, *args, **kwargs):
        self.log_widget.write(*args, **kwargs)

    def compose(self) -> ComposeResult:
        if self.subprocess:
            yield self.user_input
            self.user_input.focus()
        yield self.log_widget

    async def on_key(self, event: events.Key):
        match event.key:
            case "ctrl+l":
                self.log_widget.clear()
                event.stop()
            case "ctrl+q":
                await self.terminate_subprocess()
                event.stop()

    async def on_unmount(self):
        await self.terminate_subprocess()


class ResultScreen(ModalScreen):
    BINDINGS = [
        ("ctrl+r", "pop_screen", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.cmd_results_widget = CommandResultsWidget()
        self.cmd_results_widget.border_title = "Results"

    def compose(self) -> ComposeResult:
        yield self.cmd_results_widget
        yield Footer(self)

    def action_pop_screen(self):
        self.app.pop_screen()


class Footer(Widget):
    def __init__(self, cur_screen: Screen):
        super().__init__()
        self.cur_screen = cur_screen

    def _get_full_input(self) -> str:
        inputs = []
        for screen in self.app.screen_stack:
            if isinstance(screen, MenuScreen):
                inputs.append(screen.cur_input)
        return inputs

    def compose(self):
        inputs = self._get_full_input()

        yield Label(" > ".join(inputs))

        match self.cur_screen:
            case ResultScreen():
                bindings = [
                    ("ctrl+r", "hide results"),
                ]
                if self.cur_screen.cmd_results_widget.subprocess:
                    bindings += [
                        ("enter", "submit input"),
                        ("ctrl+q", "terminate command"),
                    ]
            case MenuScreen():
                mode = "mode: edit" if self.cur_screen.edit_mode else "mode: normal"
                bindings = [
                    ("backspace", "erase" if inputs[-1] else "back"),
                    ("ctrl+r", "show results"),
                    ("ctrl+e", mode),
                    ("ctrl+q", "quit"),
                ]
            case ChoiceArgumentInputScreen():
                screen: ChoiceArgumentInputScreen = self.cur_screen
                if screen.argument.multi:
                    bindings = [("space", "toggle option")]
                bindings = [
                    ("enter", "submit input"),
                    ("ctrl+q", "cancel"),
                ]
            case ValueArgumentInputScreen():
                bindings = []
                screen: ValueArgumentInputScreen = self.cur_screen
                if screen.argument.multi:
                    bindings = [("backspace", "delete selection")]

                bindings += [
                    ("tab", "focus next"),
                    ("shift+tab", "focus previous"),
                    ("enter", "submit input"),
                    ("ctrl+q", "cancel"),
                ]

        labels = [Label("Shortcuts:", classes="title")]
        for shortcut, description in bindings:
            labels.append(Label(f"({shortcut})", classes="help"))
            labels.append(Label(description))
        yield Horizontal(*labels, id="help-section")


class MenuScreen(Screen):
    """Main screen showing the menu interface and handling user input.

    Attributes:
        cur_input (reactive): Current user input string
    """

    BINDINGS = [
        ("backspace", "backspace_input", "Erase"),
        ("tab", "complete_input", "Complete"),
        ("ctrl+e", "change_mode", "Toggle mode"),
        ("ctrl+r", "show_results", "Show Results"),
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
        yield Footer(self)

    def action_show_results(self):
        if self.app.inplace:
            self.app.push_screen("results")

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

        async def process_argument_fn(argument: Argument):
            return await self.process_argument(argument, action="edit")

        template_resolver = CommandTemplateResolver(
            process_argument_fn=process_argument_fn
        )
        self.app.command = await template_resolver.resolve(self.menu, command.template)
        self.cur_input = ""

        if self.app.command is None:
            return

        results_widget: CommandResultsWidget = (
            self.app.results_screen.cmd_results_widget
        )
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


class YakariApp(App):
    """Main application class for Yakari command-line interface."""

    CSS_PATH = "app.css"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("ctrl+q", "quit", "Exit"),
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
