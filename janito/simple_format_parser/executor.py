"""
This module provides an executor class that can be used to associated classes with simpler parser statements.
"""
from .parser import parse_document, Statement
from typing import Optional

# Example class to be passed to our executor
class DeleteFile:
    """
    This class is used to delete a file, it's a simple class to be passed to our executor
    """
    def __init__(self, name: str):
        self.name = name

    def execute(self):
        print(f"Deleting file {self.name}")


def to_pascal_case(statement_name: str) -> str:
    """Convert space-separated statement name to PascalCase"""
    return ''.join(word.capitalize() for word in statement_name.split())


class Executor:
    def __init__(self, classes: list[type], **kwargs):
        self.classes = classes
        self.instances = []  # Track created instances
        self.global_kwargs = kwargs  # Store global kwargs to pass to handlers

    def execute(self, content: str):
        document = parse_document(content)
        for statement in document.statements:
            instance = self.execute_statement(statement)
            if instance:
                self.instances.append(instance)

    def execute_statement(self, statement: Statement) -> Optional[object]:
        pascal_case_name = to_pascal_case(statement.name)
        for class_ in self.classes:
            if class_.__name__ == pascal_case_name:
                # Merge global kwargs with statement fields, statement fields take precedence
                init_kwargs = {**self.global_kwargs, **statement.fields}
                instance = class_(**init_kwargs)
                
                # Call prepare if available
                if hasattr(instance, 'prepare'):
                    instance.prepare()
                
                # Execute substatements before main execution
                for substatement in statement.substatements:
                    method_name = to_pascal_case(substatement.name)
                    if hasattr(instance, method_name):
                        method = getattr(instance, method_name)
                        method(**substatement.fields)
                    else:
                        raise AttributeError(f"Class {class_.__name__} has no method {method_name}")
                
                instance.execute()
                return instance
        return None


def test_executor():
    # Test class that records its execution
    class ModifyFile:
        def __init__(self, path: str):
            self.path = path
            self.executed = False
            self.replaced_block = False
            self.replacement_params = None
            self.prepared = False

        def prepare(self):
            self.prepared = True

        def execute(self):
            self.executed = True

        def ReplaceBlock(self, start_context: str, end_context: str, new_content: str):
            assert self.prepared, "prepare() should be called before substatements"
            self.replaced_block = True
            self.replacement_params = {
                'start_context': start_context,
                'end_context': end_context,
                'new_content': new_content
            }

    # Create an executor
    executor = Executor([ModifyFile])

    # Test statement with substatement
    content = """
    Modify File
    path: test.txt
    - Replace Block
      start_context: old content
      end_context: end content
      new_content: new content
    ===
    """
    executor.execute(content)
    
    # Verify the instance and substatement were executed
    assert len(executor.instances) == 1
    instance = executor.instances[0]
    assert isinstance(instance, ModifyFile)
    assert instance.prepared, "prepare() was not called"
    assert instance.executed
    assert instance.path == "test.txt"
    assert instance.replaced_block
    assert instance.replacement_params == {
        'start_context': 'old content',
        'end_context': 'end content',
        'new_content': 'new content'
    }

    # Test method name conversion
    assert to_pascal_case("Replace Block") == "ReplaceBlock"
    assert to_pascal_case("Add Content") == "AddContent"

    print("All executor tests passed!")


if __name__ == "__main__":
    test_executor()
