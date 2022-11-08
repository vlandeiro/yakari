import os
import pkgutil
from pathlib import Path
from pprint import pprint
from typing import Dict, List

import toml
from attrs import asdict, define

from .action import Argument


@define
class Config:
    actions: Dict[str, Argument]

    @classmethod
    def from_toml(cls, filepath: Path) -> "Config":
        with open(filepath) as fd:
            config_data = toml.load(fd)
        return cls.from_dict(config_data)

    @classmethod
    def from_tomls(cls, data) -> "Config":
        config_data = toml.loads(data.decode())
        return cls.from_dict(config_data)

    @classmethod
    def from_dict(cls, config: Dict) -> "Config":
        actions = {}
        for action_name, arguments_dict in config.items():
            actions[action_name] = Argument.from_dict(action_name, arguments_dict)

        return Config(actions)

    @classmethod
    def from_command_name(cls, command_name: str) -> "Config":
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
