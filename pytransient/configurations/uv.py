from ..types import Menu, Command, ChoiceArgument, FlagArgument, Prefix, ValueArgument
from pprint import pprint

python_version_prefix = Prefix(
    name="Manage python versions and installations",
    arguments={
        "-p": ChoiceArgument(
            name="--python-preference",
            template="{self.name} {self.selected}",
            choices=["only-managed", "managed", "system", "only-system"],
        ),
        "-n": FlagArgument(
            name="--no-python-downloads",
        ),
    },
    commands={
        "i": Command(
            name="install",
            template="uv python install {self.resolved_arguments} {self.dynamic_arguments}",
            dynamic_arguments=[
                ValueArgument(name="targets", value_type=str),
            ],
        ),
        "l": Command(name="list", template="uv python list {self.resolved_arguments}"),
    },
)

package_argument = ValueArgument(name="package", value_type=str)
dependency_mgmt_prefix = Prefix(
    name="Manage dependencies",
    arguments={
        "-d": FlagArgument(name="--dev"),
        "-o": ValueArgument(
            name="--optional", value_type=str, template="{self.name} {self.value}"
        ),
        "-g": ValueArgument(
            name="--group", value_type=str, template="{self.name} {self.value}"
        ),
    },
    commands={
        "a": Command(
            name="add",
            description="Add dependencies to the project",
            template="uv add {self.resolved_arguments} {self.dynamic_arguments}",
            dynamic_arguments=[package_argument],
        ),
        "r": Command(
            name="remove",
            description="Remove dependencies from the project",
            template="uv remove {self.resolved_arguments} {self.dynamic_arguments}",
            dynamic_arguments=[package_argument],
        ),
    },
)
main_menu = Menu(
    name="uv",
    prefixes={
        "d": dependency_mgmt_prefix,
        "p": python_version_prefix,
    },
)

if __name__ == "__main__":
    pprint(main_menu.model_dump())
