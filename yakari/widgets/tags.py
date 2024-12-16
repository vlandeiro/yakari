from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Label


class Tag(Widget):
    can_focus = True
    can_focus_children = False

    value: reactive[str] = reactive(str, recompose=True)

    BINDINGS = [
        ("backspace", "delete_this", "delete"),
    ]

    class Deleted(Message):
        def __init__(self, tag):
            super().__init__()
            self.tag = tag

    def __init__(self, value: str):
        super().__init__()
        self.value = value

    def compose(self) -> ComposeResult:
        yield Button("X")
        yield Label(self.value)

    def delete(self):
        self.post_message(Tag.Deleted(self))

    def on_button_pressed(self, event: Button.Pressed):
        self.delete()

    def action_delete_this(self):
        self.delete()


class TagsCollection(Widget):
    can_focus = False
    can_focus_children = True

    tags: reactive[list[Tag]] = reactive(default=list, recompose=True)

    def _sanitize_tag(self, tag: str | Tag) -> Tag:
        if isinstance(tag, str):
            tag = Tag(value=tag)
        return tag

    def __init__(self, tags: list[str | Tag] | None = None):
        super().__init__()
        if self.tags:
            self.tags = [self._sanitize_tag(tag) for tag in tags]
            self.mutate_reactive(TagsCollection.tags)

    def add_tag(self, *tags: str | Tag):
        for tag in tags:
            tag = self._sanitize_tag(tag)
            self.tags.append(tag)
        self.mutate_reactive(TagsCollection.tags)

    def delete_tag(self, tag: str | Tag):
        tag = self._sanitize_tag(tag)
        self.tags.remove(tag)
        self.mutate_reactive(TagsCollection.tags)

    def on_tag_deleted(self, message: Tag.Deleted):
        self.delete_tag(message.tag)

    def compose(self) -> ComposeResult:
        if self.tags:
            scrollable = ScrollableContainer(*self.tags)
            scrollable.can_focus = False
            yield scrollable

    @property
    def values(self):
        return [tag.value for tag in self.tags]
