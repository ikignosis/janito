from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto
from pathlib import Path

class MockOperationType(Enum):
    CREATE = auto()
    MODIFY = auto()
    REMOVE = auto()

@dataclass
class MockOperation:
    """Base class for mock operations"""
    operation_type: MockOperationType
    name: str
    reason: str

@dataclass
class CreateOperation(MockOperation):
    """Operation for creating new files"""
    content: str

    def __init__(self, name: str, content: str, reason: str = "Create new file"):
        super().__init__(MockOperationType.CREATE, name, reason)
        self.content = content

@dataclass
class ModifyOperation(MockOperation):
    """Operation for modifying existing files"""
    content: str
    original_content: str

    def __init__(self, name: str, content: str, original_content: str, reason: str = "Modify existing file"):
        super().__init__(MockOperationType.MODIFY, name, reason)
        self.content = content
        self.original_content = original_content

@dataclass
class RemoveOperation(MockOperation):
    """Operation for removing files"""
    original_content: Optional[str] = None

    def __init__(self, name: str, original_content: Optional[str] = None, reason: str = "Remove file"):
        super().__init__(MockOperationType.REMOVE, name, reason)
        self.original_content = original_content