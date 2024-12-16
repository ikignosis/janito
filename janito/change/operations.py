from enum import Enum, auto

class TextOperation(Enum):
    """Supported text modification operations"""
    REPLACE = auto()
    APPEND = auto()
    DELETE = auto()