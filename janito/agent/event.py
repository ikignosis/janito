from enum import Enum, auto
from typing import Any


class EventType(Enum):
    CONTENT = auto()
    INFO = auto()
    SUCCESS = auto()
    ERROR = auto()
    PROGRESS = auto()
    WARNING = auto()
    STDOUT = auto()
    STDERR = auto()
    STREAM = auto()
    STREAM_TOOL_CALL = auto()
    STREAM_END = auto()
    TOOL_CALL = auto()
    TOOL_RESULT = auto()


class Event:
    def __init__(self, type: EventType, payload: Any = None):
        self.type = type
        self.payload = payload
