from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import OptionList as BaseOptionList
from textual.widgets.option_list import Option, Separator


class OptionList(BaseOptionList):
    BINDINGS = [("enter", "select", "select")]
    pass


class SuggestionsWidget(Widget):
    class SuggestionSelected(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    def __init__(self, suggested_values: list[str], *args, **kwargs):
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

    def on_option_list_option_selected(self, message: OptionList.OptionSelected):
        value = message.option.prompt
        self.post_message(self.SuggestionSelected(value))
        message.stop()

    def compose(self) -> ComposeResult:
        yield self.suggestions_widget
