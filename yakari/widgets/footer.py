from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer as BaseFooter
from textual.widgets import Label


class Footer(BaseFooter):
    def _get_full_input(self) -> str:
        inputs = []
        for screen in self.app.screen_stack:
            if hasattr(screen, "cur_input"):
                inputs.append(screen.cur_input)
        return inputs

    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return

        inputs = self._get_full_input()

        yield Label(" > ".join(inputs), id="cur-input")

        labels = [Label("Shortcuts:", classes="title")]
        bindings = [
            binding
            for (_, binding, enabled, tooltip) in self.app.active_bindings.values()
            if binding.show
        ]
        for binding in bindings:
            labels.append(Label(f"({binding.key})", classes="help"))
            labels.append(Label(binding.description))
        yield Horizontal(*labels, id="help-section")

        edit_mode = getattr(self.app.screen, "edit_mode", None)
        hint = "edit" if edit_mode else "toggle"
        yield Label(f"Mode: {hint}", id="hint-edit")
