class Command:
    def __init__(self, binding: str, underlying: str = "", description: str = ""):
        self.binding = binding
        self.underlying = underlying
        self.description = description
        self._is_active = False

    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool):
        assert isinstance(value, bool)
        self._is_active = value

    def toggle(self):
        self.is_active = not self.is_active

    def serialize(self):
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}
