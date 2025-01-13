from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class ChangeType(Enum):
    REPLACE = auto()
    DELETE = auto()
    INSERT = auto()
    APPEND = auto()
    MOVE = auto()

@dataclass
class Change:
    """ A change of content in a file stored so that it can be displayed as a change view """
    change_type: ChangeType
    original_content: Optional[List[str]]
    new_content: Optional[List[str]]
    start_line: int
    end_line: int
