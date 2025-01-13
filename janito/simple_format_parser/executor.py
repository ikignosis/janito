"""
This module provides an executor class that can be used to associated classes with simpler parser statements.
"""
from .parser import parse_document, Statement
from typing import Optional


class ExecutorError(Exception):
    """Base class for executor errors"""
    pass


class UnknownStatementError(ExecutorError):
    """Raised when a statement has no matching handler class"""
    def __init__(self, statement_name: str, available_handlers: list[str]):
        self.statement_name = statement_name
        self.available_handlers = available_handlers
        message = (
            f"No handler class found for statement '{statement_name}'. "
            f"Available handlers: {', '.join(available_handlers)}"
        )
        super().__init__(message)


def to_pascal_case(statement_name: str) -> str:
    """Convert space-separated statement name to PascalCase"""
    return ''.join(word.capitalize() for word in statement_name.split())


class Executor:
    def __init__(self, classes: list[type], **kwargs):
        self.classes = classes
        self.instances = []  # Track created instances
        self.global_kwargs = kwargs  # Store global kwargs to pass to handlers
        
        # Store available handler names for error messages
        self.available_handlers = [cls.__name__ for cls in classes]

    def execute(self, content: str):
        document = parse_document(content)
        for statement in document.statements:
            instance = self.execute_statement(statement)
            if instance:
                self.instances.append(instance)

    def execute_statement(self, statement: Statement) -> Optional[object]:
        pascal_case_name = to_pascal_case(statement.name)
        
        # Check if we have a handler for this statement
        matching_classes = [cls for cls in self.classes if cls.__name__ == pascal_case_name]
        
        if not matching_classes:
            raise UnknownStatementError(statement.name, self.available_handlers)
            
        class_ = matching_classes[0]
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
