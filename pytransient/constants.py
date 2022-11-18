from enum import Enum


class ArgumentType(str, Enum):
    ACTION = "action"
    NAMED = "named"
    FLAG = "flag"
    POSITIONAL = "positional"


KIND = "_kind"
NAME = "_name"
HELP_MSG = "_help"
RENDERED_NAME = "_render"
KEY = "_key"
VALUE_TYPE = "_value_type"
VALID_KINDS = set(ArgumentType)
IS_ACTIVE = "_active"
VALUE = "_value"
