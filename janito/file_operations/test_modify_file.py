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
            lines:
                .def another_function():
        - Insert
            lines:
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

def test_replace_then_append(sample_file):
    """Test replacing content and then appending without a new selection.
    
    Verifies that append operation uses the range from the replaced content."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modifications
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
        - Append
            new_content:
                .    return True
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "def new_function():" in result
    assert "    print(\"New\")" in result
    assert "    return True" in result
    # Verify order
    assert "print(\"New\")\n    return True\n\ndef another_function()" in result 

def test_selection_after_operations(sample_file):
    """Test that selected range is properly updated after each operation."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    modify_file = executor.ModifyFile(sample_file)
    modify_file.prepare()
    
    # Test Replace
    modify_file.SelectOver("def old_function():", "    return False")
    modify_file.Replace("def new_function():\n    return True")
    assert modify_file.selected_range == (0, 2)  # Should cover new content
    
    # Test Append without new selection
    modify_file.Append("    print('Extra')")
    assert modify_file.selected_range == (0, 3)  # Should include appended line
    
    # Test Insert
    modify_file.SelectExact("def another_function():")
    modify_file.Insert("# Comment\n# Another")
    assert modify_file.selected_range == (4, 7)  # Should include inserted lines and selection
    
    # Test Delete
    modify_file.SelectExact("    print('Extra')")
    modify_file.Delete()
    assert modify_file.selected_range is None  # Should clear selection after delete 

def test_append_to_end_of_file(sample_file):
    """Test appending content when no lines are selected.
    
    Should append to the end of the file."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Append
            new_content:
                .# Added at the end
                .# More content
    """)
    
    # Read the modified file
    result = Path(executor.target_dir / sample_file.name).read_text()
    
    # Original content should be unchanged
    assert "def old_function():" in result
    assert "def another_function():" in result
    assert "def last_function():" in result
    
    # New content should be at the end
    assert result.endswith("# Added at the end\n# More content\n") 