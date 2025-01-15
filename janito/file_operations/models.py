from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

class ChangeType(Enum):
    """Types of changes that can be made to a file."""
    REPLACE = auto()  # Replace old lines with new lines
    DELETE = auto()   # Delete sequence of lines
    ADD = auto()      # Add new lines after current lines or at end of file

@dataclass
class Change:
    """A change of content in a file stored so that it can be displayed as a change view.
    
    Attributes:
        change_type: Type of change (Replace, Delete, or Add)
        original_content: Lines that were modified/deleted, or lines after which content was added
        new_content: New lines that were added/replaced, or empty list for deletion
        start_line: Starting line number of the change (0-based)
        end_line: Ending line number after the change (0-based)
    """
    change_type: ChangeType
    original_content: List[str]
    new_content: List[str]
    start_line: int
    end_line: int

@dataclass
class OperationFailure:
    """Represents a failed file operation with details."""
    operation_type: ChangeType
    file_path: Path
    search_content: str
    error_message: str
