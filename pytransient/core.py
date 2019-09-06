from typing import List


class Command:
    def __init__(
        self, binding: str, action: str = "", description: str = "", move_to: str = ""
    ):
        self.binding = binding
        self.action = action
        self.description = description
        self.move_to = move_to

    def to_dict(self):
        serialized = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        cls = self.__class__
        serialized["__class__"] = f"{cls.__module__}.{cls.__name__}"
        return serialized


class Argument(Command):
    def __init__(
        self, binding: str, action: str = "", description: str = "", value: str = None
    ):
        super().__init__(binding=binding, action=action, description=description)
        self._is_active = False
        self.value = value

    @property
    def is_editable(self):
        return self.action.endswith("=")

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool):
        assert isinstance(value, bool)
        self._is_active = value

    def toggle(self):
        self.is_active = not self.is_active


class Group:
    def __init__(self, title: str, commands: List[Command]):
        self.title = title
        self.commands = commands

    def to_dict(self):
        return {self.title: [c.to_dict() for c in self.commands]}


class Menu:
    def __init__(self, name: str, groups: List[Group]):
        self.name = name
        self.groups = groups

    def to_dict(self):
        return {self.name: [g.to_dict() for g in self.groups]}
