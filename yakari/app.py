from pathlib import Path

from textual.app import App

from .types import Menu
from .screens import MenuScreen, ResultsScreen


class YakariApp(App):
    CSS_PATH = "app.css"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        ("ctrl+q", "quit", "quit"),
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
        self.results_screen = ResultsScreen()

    def on_mount(self) -> None:
        self.install_screen(self.results_screen, "results")
        self.install_screen(self.menu_screen, self.menu.name)
        self.push_screen(self.menu.name)
