from typing import List
from .operations import CreateOperation, ModifyOperation, RemoveOperation, MockOperation

def get_mock_changes() -> List[MockOperation]:
    """Get predefined mock changes for demo"""
    return [
        CreateOperation(
            name="example/hello.py",
            content="def greet():\n    print('Hello, World!')\n"
        ),
        ModifyOperation(
            name="example/utils.py",
            content="def process():\n    return 'Processed'\n",
            original_content="def old_process():\n    return 'Old'\n"
        ),
        RemoveOperation(
            name="example/obsolete.py",
            original_content="# Obsolete code\n"
        )
    ]