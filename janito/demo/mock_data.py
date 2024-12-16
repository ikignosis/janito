from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class MockFileChange:
    """Mock file change for demo purposes"""
    name: str
    content: str
    operation: str  # create, modify, remove
    original_content: Optional[str] = None

def get_mock_changes() -> List[MockFileChange]:
    """Get predefined mock changes for demo"""
    return [
        MockFileChange(
            name="example/hello.py",
            content="def greet():\n    print('Hello, World!')\n",
            operation="create"
        ),
        MockFileChange(
            name="example/utils.py",
            content="def process():\n    return 'Processed'\n",
            operation="modify",
            original_content="def old_process():\n    return 'Old'\n"
        ),
        MockFileChange(
            name="example/obsolete.py",
            content="",
            operation="remove",
            original_content="# Obsolete code\n"
        )
    ]