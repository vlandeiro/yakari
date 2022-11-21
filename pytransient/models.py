from typing import Dict, List, Optional, Union, Set
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.style import Style
from rich.text import Text
from attrs import asdict, define
import os
import pkgutil
from pathlib import Path
from pprint import pprint
from typing import Dict, List
import networkx as nx
from networkx.algorithms.dag import topological_sort

import toml
from attrs import asdict, define


@define
class Command:
    name: str
    base: List[str]
    parameters: List["CommandParameter"]
    help_message: str = ""
    key: Optional[str] = None

    @classmethod
    def from_dict(cls, name, config, arguments_map) -> "Command":
        parameters = []
        for parameter_config in config.get("parameters", []):
            parameters.append(
                CommandParameter(
                    param=arguments_map[parameter_config["name"]],
                    render=parameter_config["render"],
                    is_optional=parameter_config.get("optional", False),
                )
            )
        return cls(
            name=name,
            base=config["base"],
            parameters=parameters,
            help_message=config.get("help", ""),
            key=config.get("key")
        )

    def to_list(self) -> List[str]:
        cmd = self.base[:]
        for parameter in self.parameters:
            param = parameter.param
            if not param.is_active:
                continue

            if isinstance(param, Flag):
                param_rendered = parameter.render
            elif isinstance(param, Argument):
                param_rendered = parameter.render.format(**{param.name: param.value})
            cmd.append(param_rendered)

        return cmd

@define
class CommandParameter:
    param: Union["Argument", "Flag"]
    render: str
    is_optional: bool


@define
class Argument:
    name: str
    key: str
    value: Optional[str] = None
    help_message: str = ""
    is_active: bool = False

@define
class Flag:
    name: str
    key: str
    help_message: str = ""
    is_active: bool = False


@define
class Transient:
    name: str
    keymap: Dict[str, Union["Transient", Command, Argument, Flag]]
    disabled_keys: Set[str]
    highlighted_keys: Set[str]
    help_message: str = ""

    @property
    def active_keys(self):
        return set(
            [
                key
                for key, target in self.keymap.items()
                if getattr(target, "is_active", False)
            ]
        )

    @classmethod
    def empty(cls) -> "Transient":
        return Transient("main", dict(), set(), "")

    @classmethod
    def from_toml(cls, filepath: Path) -> "Transient":
        with open(filepath) as fd:
            config_data = toml.load(fd)
        return cls.from_dict(config_data)

    @classmethod
    def from_tomls(cls, data) -> "Transient":
        config_data = toml.loads(data.decode())
        return cls.from_dict(config_data)

    @classmethod
    def from_dict(cls, config: Dict) -> "Transient":
        transients = dict()

        # create directed graph of transients
        digraph = cls._make_transients_digraph(config)
        sorted_transients = list(topological_sort(digraph))
        for transient_name in reversed(sorted_transients):
            transient_config = config[transient_name]
            transient_keymap = dict()
            name_to_argument_map = dict()

            for target_name, target_config in transient_config.items():
                key = target_config["key"]
                kind = target_config["kind"]

                if kind == "flag":
                    target_value = Flag(
                        name=target_name, key=key, help_message=target_config.get("help", "")
                    )
                    name_to_argument_map[target_name] = target_value

                elif kind == "argument":
                    target_value = Argument(
                        name=target_name,
                        key=key,
                        value=target_config.get("default", None),
                        help_message=target_config.get("help", ""),
                    )
                    name_to_argument_map[target_name] = target_value

                elif kind == "command":
                    target_value = Command.from_dict(
                        name=target_name,
                        config=target_config,
                        arguments_map=name_to_argument_map,
                    )

                elif kind == "transient":
                    target_value = transients[target_name]

                else:
                    raise ValueError(f"kind == {kind} is not supported")

                transient_keymap[key] = target_value
            transients[transient_name] = cls(
                name=transient_name,
                keymap=transient_keymap,
                disabled_keys=set(),
                highlighted_keys=set(),
                help_message="",
            )

        return transients["main"]

    @staticmethod
    def _make_transients_digraph(config: Dict) -> nx.DiGraph:
        edges = []
        for transient_name, transient_config in config.items():
            for target_name, target_config in transient_config.items():
                if target_config["kind"] == "transient":
                    edges.append((transient_name, target_name))
        return nx.DiGraph(edges)

    @classmethod
    def from_command_name(cls, command_name: str) -> "Transient":
        """
        Tries to load the configuration from local ``$HOME/.pytransient``
        folder first.  If there are no match, tries to load the configuration
        from the package pre-packed configurations. If there are still no
        match, error out.
        """
        local_fpath = Path(os.environ["HOME"]) / ".pytransient" / f"{command_name}.toml"
        if local_fpath.is_file():
            return cls.from_toml(local_fpath)

        try:
            data = pkgutil.get_data(
                "pytransient.configurations", f"{command_name}.toml"
            )
            return cls.from_tomls(data)
        except FileNotFoundError:
            log.error(f"No configuration file for command '{command_name}'.")
            sys.exit(1)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(show_header=False, box=None)

        table.add_column("Key", justify="left", style="cyan")
        table.add_column("Name")
        table.add_column("Help")
        table.add_column("Value", style="emphasize")

        for key, target in self.keymap.items():
            style = Style()
            if key in self.active_keys:
                style += Style(bold=True)
            if key in self.disabled_keys:
                style += Style(dim=True)

            target_name = Text(target.name)
            if key in self.highlighted_keys:
                target_name.stylize(Style(underline=True))
            table.add_row(
                key,
                target_name,
                target.help_message,
                getattr(target, "value", ""),
                style=style,
            )

        yield table


if __name__ == "__main__":
    fpath = Path(__file__).resolve().parent / "configurations" / "git_new.toml"
    t = Transient.from_toml(fpath)
    # t.active_keys.add("b")
    # t.disabled_keys.add("b")
    # t.active_keys.add("f")
    # t.disabled_keys.add("l")
    console = Console()
    console.print(t)

    t = t.keymap["b"]
    console.print()
    console.print(t)
