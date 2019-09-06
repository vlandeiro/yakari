from prompt_toolkit import Application, HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout

root_container = Window(
    content=FormattedTextControl(text="Hello world"), always_hide_cursor=True
)

layout = Layout(root_container)

kb = KeyBindings()


@kb.add("q")
def exit_(event):
    """
    Pressing Ctrl-Q will exit the user interface.

    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    """
    event.app.exit()


@kb.add("t")
def replace_content(event):
    root_container.content = FormattedTextControl(text=HTML("<b>Hello</b> world"))


@kb.add("-", "t")
def replace_content(event):
    root_container.content = FormattedTextControl(text=HTML("<i>Hello</i> world"))


app = Application(layout=layout, key_bindings=kb, full_screen=False)
app.run()
