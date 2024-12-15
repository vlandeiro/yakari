from textual.app import ComposeResult
from textual.screen import ModalScreen

from ..widgets import Footer, CommandRunner


class ResultsScreen(ModalScreen):
    BINDINGS = [
        ("ctrl+l", "clear_screen", "clear"),
        ("ctrl+r", "pop_screen", "hide results"),
    ]

    def __init__(self):
        super().__init__()
        self.cmd_runner = CommandRunner()
        self.cmd_runner.border_title = "Results"

    def compose(self) -> ComposeResult:
        yield self.cmd_runner
        yield Footer()

    def action_pop_screen(self):
        self.app.pop_screen()

    def action_clear_screen(self):
        self.cmd_runner.log_widget.clear()
