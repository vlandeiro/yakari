from prompt_toolkit import Application, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout import (
    Dimension,
    Layout,
    FormattedTextControl,
    Window,
    VSplit,
    HSplit,
)
from prompt_toolkit.widgets import TextArea, Label
from .core import Menu, Argument


class TransientApp:
    def __init__(self, action: str, main_menu: Menu):
        self.action = action
        self.menu_stack = [main_menu]
        self._setup_app()

    def edit_argument_container(self, argument: Argument):
        def set_argument_value(buff):
            argument.value = buff

        return TextArea(
            multiline=False,
            scrollbar=False,
            width=Dimension(weight=4),
            get_line_prefix=lambda line, wrap_count: HTML(f"<b>{argument.action}</b>"),
            accept_handler=set_argument_value,
        )

    def _setup_app(self):
        self.display_buffer = TextArea(
            height=Dimension(preferred=100),
            focus_on_click=True,
            dont_extend_height=True,
            dont_extend_width=True,
            scrollbar=True,
        )
        self.transient_menu = TextArea(
            height=Dimension(preferred=30),
            read_only=True,
            dont_extend_height=True,
            dont_extend_width=True,
        )
        self.edit_arg_menu = TextArea(
            height=Dimension(preferred=10),
            focus_on_click=True,
            dont_extend_height=True,
            dont_extend_width=True,
            multiline=False,
            scrollbar=False,
        )
        self.root = HSplit(
            [self.display_buffer, self.transient_menu, self.edit_arg_menu],
            padding_char="-",
            padding=1,
        )
        self.layout = Layout(self.root)
        self.kb = KeyBindings()
        self.app = Application(
            layout=self.layout, key_bindings=self.kb, full_screen=False
        )
        self.kb.add("c-q")(self._exit)

    def _exit(self, event):
        event.app.exit()

    def run(self, *args, **kwargs):
        self.app.run(*args, **kwargs)
