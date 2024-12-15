from typing import List

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import OptionList, SelectionList

from ..types import ChoiceArgument
from ..widgets import Footer


class ChoiceArgumentInputScreen(ModalScreen[int | List[str] | None]):
    """A modal screen for selecting from a list of choices for an argument.

    Args:
        argument (ValueArgument): The argument containing the choices
    """

    BINDINGS = [
        ("enter", "submit_input", "submit input"),
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

    def action_submit_input(self):
        result = getattr(self.widget, self.result_attr)
        self.dismiss(result)

    def action_cancel(self):
        self.dismiss(None)
