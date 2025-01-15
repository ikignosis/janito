import os
import pytest
import tempfile
from pathlib import Path
from .file_operations import FileOperationExecutor

@pytest.fixture
def sample_file() -> Path:
    """Fixture to create a sample file for testing.
    
    Returns:
        Path: Path to the created sample file
    """
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

def test_replace_operation(sample_file: Path):
    """Test replacing old lines with new lines.
    
    Args:
        sample_file (Path): Path to the test file
    """
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Replace
            old_lines:
                .def old_function():
                .    print("Hello")
                .    return False
            new_lines:
                .def new_function():
                .    print("New")
                .    return True
    """)
    
    # Read the modified file
    result = (executor.target_dir / sample_file.name).read_text()
    assert "def new_function():" in result
    assert "print(\"New\")" in result
    assert "def old_function():" not in result
    assert "print(\"Hello\")" not in result

def test_delete_operation(sample_file: Path):
    """Test deleting a sequence of lines.
    
    Args:
        sample_file (Path): Path to the test file
    """
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Delete
            old_lines:
                .def old_function():
                .    print("Hello")
                .    return False
    """)
    
    # Read the modified file
    result = (executor.target_dir / sample_file.name).read_text()
    assert "def old_function():" not in result
    assert "print(\"Hello\")" not in result
    assert "def another_function():" in result
    assert "def last_function():" in result

def test_add_after_lines(sample_file: Path):
    """Test adding new lines after specified current lines.
    
    Adds new function implementation after 'old_function'."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Add
            current_lines:
                .def old_function():
                .    print("Hello")
                .    return False
            new_lines:
                .
                .def new_function():
                .    print("New")
                .    return True
    """)
    
    # Read the modified file
    result = (executor.target_dir / sample_file.name).read_text()
    # Verify both functions exist
    assert "def old_function():" in result
    assert "def new_function():" in result
    # Verify order
    assert result.index("def old_function()") < result.index("def new_function()")

def test_add_to_end(sample_file: Path):
    """Test adding new lines at the end of file when no current_lines specified."""
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Add
            new_lines:
                .# Added at the end
                .def final_function():
                .    print("Final")
                .    return None
    """)
    
    # Read the modified file
    result = (executor.target_dir / sample_file.name).read_text()
    
    # Original content should be unchanged
    assert "def old_function():" in result
    assert "def another_function():" in result
    assert "def last_function():" in result
    
    # New content should be at the end
    assert result.endswith("def final_function():\n    print(\"Final\")\n    return None\n")

def test_multiple_operations(sample_file: Path):
    """Test multiple operations in sequence.
    
    1. Replace old_function
    2. Delete another_function
    3. Add new content after last_function
    """
    
    # Create executor
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modifications
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Replace
            old_lines:
                .def old_function():
                .    print("Hello")
                .    return False
            new_lines:
                .def new_function():
                .    print("New")
                .    return True
        - Delete
            old_lines:
                .def another_function():
                .    print("World")
                .    return True
        - Add
            current_lines:
                .def last_function():
                .    print("!")
                .    return None
            new_lines:
                .
                .def added_function():
                .    print("Added")
                .    return True
    """)
    
    # Read the modified file
    result = (executor.target_dir / sample_file.name).read_text()
    
    # Verify replacements
    assert "def new_function():" in result
    assert "def old_function():" not in result
    
    # Verify deletion
    assert "def another_function():" not in result
    
    # Verify addition and order
    assert "def last_function():" in result
    assert "def added_function():" in result
    assert result.index("def last_function()") < result.index("def added_function()") 