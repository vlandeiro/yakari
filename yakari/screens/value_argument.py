import shelve

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList

from .. import constants as C
from ..types import ValueArgument
from ..widgets import ArgumentInput, Footer, SuggestionsWidget


class ValueArgumentInputScreen(ModalScreen[str | None]):
    """A modal screen for entering a value for an argument.

    Args:
        argument (ValueArgument): The argument to get input for
    """

    BINDINGS = [
        ("ctrl+q", "cancel", "cancel"),
    ]

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

    def action_cancel(self):
        self.dismiss(None)

    def on_argument_input_submitted(self, message: ArgumentInput.Submitted):
        self.dismiss(message.value)

    def on_suggestions_widget_suggestion_selected(
        self, message: SuggestionsWidget.SuggestionSelected
    ):
        self.input_widget.set_value(message.value)
        self.input_widget.focus()
        message.stop()

    def compose(self) -> ComposeResult:
        if self.suggestions_widget is not None:
            yield self.suggestions_widget
        yield self.input_widget
        yield Footer()
