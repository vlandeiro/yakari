import shelve

from textual.app import ComposeResult
from textual.message import Message
from textual.suggester import SuggestFromList
from textual.widget import Widget
from textual.widgets import Input as BaseInput

from .. import constants as C
from ..types import Argument, History
from .tags import TagsCollection


class Input(BaseInput):
    BINDINGS = [("enter", "submit", "submit")]


class ArgumentInput(Widget):
    BINDINGS = [("ctrl+q", "cancel", "cancel")]

    class Submitted(Message):
        def __init__(self, value: list[str] | str) -> None:
            self.value = value
            super().__init__()

    def __init__(
        self,
        argument: Argument,
        suggested_values: list[str] | None = None,
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
