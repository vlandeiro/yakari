from typing import List

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import (
    SelectionList as BaseSelectionList,
    OptionList as BaseOptionList,
)
from textual.message import Message

from ..types import ChoiceArgument
from ..widgets import Footer


class SelectionList(BaseSelectionList):
    BINDINGS = [
        ("enter", "submit_selection", "submit"),
    ]

    class SelectionSubmitted(Message):
        def __init__(self, selection):
            super().__init__()
            self.selection = selection

    def action_submit_selection(self):
        self.post_message(self.SelectionSubmitted(self.selected))


class OptionList(BaseOptionList):
    BINDINGS = [("enter", "select", "submit")]
    pass


class ChoiceArgumentInputScreen(ModalScreen[int | List[str] | None]):
    """A modal screen for selecting from a list of choices for an argument.

    Args:
        argument (ValueArgument): The argument containing the choices
    """

    BINDINGS = [
        ("enter", "submit_input", "submit"),
        ("ctrl+q", "cancel", "cancel"),
    ]

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
        yield Footer()

    def on_option_list_option_selected(self, message: OptionList.OptionSelected):
        self.dismiss(message.option.prompt)

    def on_selection_list_selection_submitted(
        self, message: SelectionList.SelectionSubmitted
    ):
        self.dismiss(message.selection)

    def action_cancel(self):
        self.dismiss(None)
