from enum import Enum, auto


class ActionType(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
