import os
import pytest
import tempfile
from pathlib import Path
from .file_operations import FileOperationExecutor

@pytest.fixture
def sample_file():
    """Fixture to create a sample file for testing."""
    with tempfile.TemporaryDirectory() as input_dir:
        sample_file = Path(input_dir) / "sample.py"
        sample_file.write_text("""def old_function():
    print("Hello")
    return False

def another_function():
    print("World")
    return True

def last_function():
    print("!")
    return None
""")
        yield sample_file

def test_select_between(sample_file):
    """Test selecting and replacing content between two functions.
    
    Uses '- Select Between' to select the empty line between functions,
    followed by '- Replace' to add comments."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Select Between
            start_lines:
                .    return False
            end_lines:
                .def another_function():
        - Replace
            new_content:
                .# Separating functions with a comment
                .# This is the next function below
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    # Check that functions are intact
    assert "def old_function():" in result
    assert "    return False" in result
    assert "def another_function():" in result
    # Check that new content was inserted between them
    assert "return False\n# Separating functions with a comment\n# This is the next function below\ndef another_function()" in result 

def test_select_over(sample_file):
    """Test selecting and deleting an entire function.
    
    Uses '- Select Over' to select the complete 'old_function' including its definition 
    and body, followed by '- Delete' to remove it."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Select Over
            start_lines:
                .def old_function():
            end_lines:
                .    return False
        - Delete
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "def old_function():" not in result
    assert "return False" not in result
    assert "def another_function():" in result

def test_select_exact(sample_file):
    """Test selecting and deleting a specific line within a function.
    
    Uses '- Select Exact' to select a specific print statement,
    followed by '- Delete' to remove just that line."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Select Exact
            lines:
                .    print("Hello")
        - Delete
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "print(\"Hello\")" not in result
    assert "def old_function():" in result
    assert "return False" in result

def test_replace_operation(sample_file):
    """Test replacing an entire function with a new implementation.
    
    Replaces 'old_function' that returns False with 'new_function' that
    prints 'New' and returns True."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Select Over
            start_lines:
                .def old_function():
            end_lines:
                .    return False
        - Replace
            new_content:
                .def new_function():
                .    print("New")
                .    return True
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "def new_function():" in result
    assert "print(\"New\")" in result
    assert "def old_function():" not in result

def test_insert_operation(sample_file):
    """Test inserting comments before a function definition.
    
    Adds two comment lines immediately before the 'another_function' definition."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Select Exact
            content:
                .def another_function():
        - Insert
            new_content:
                .# New function below
                .# Important stuff
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "# New function below\n# Important stuff\ndef another_function():" in result

def test_append_operation(sample_file):
    """Test appending comments after a function implementation.
    
    Adds two comment lines after the 'old_function' implementation,
    before the next function begins."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Select Over
            start_lines:
                .def old_function():
            end_lines:
                .    return False
        - Append
            new_content:
                .# End of first function
                .# More comments
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "return False\n# End of first function\n# More comments\n\ndef another_function()" in result 