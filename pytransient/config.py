from pathlib import Path
import toml
from pprint import pprint

from .action import Argument
from typing import Dict, List
from attrs import asdict, define

@define
class Config:
    actions: Dict[str, Argument]

    @classmethod
    def from_toml(cls, filepath: Path) -> "Config":
        with open(filepath) as fd:
            config_data = toml.load(fd)
        return cls.from_dict(config_data)

    @classmethod
    def from_dict(cls, config: Dict) -> "Config":
        actions = {}
        for action_name, arguments_dict in config.items():
            actions[action_name] = Argument.from_dict(action_name, arguments_dict)

        return Config(actions)


if __name__ == "__main__":
    from rich.console import Console

    console = Console()
    config = Config.from_toml("./configurations/git.toml")


    console.print(asdict(config))
    console.print(config.actions["git"].arguments[0].render())
