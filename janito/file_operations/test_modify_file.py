import pytest
from pathlib import Path
from .file_operations import FileOperationExecutor
from .line_finder import MatchMethod

@pytest.fixture
def sample_file(tmp_path) -> Path:
    """Create a sample file for testing with various formatting."""
    content = """
def old_function():
    print("Hello")
    return False

def another_function():
    x = 1
    return True

class MyClass:
    def __init__(self):
        self.x = 1
        self.y = 2

    def method(self) -> bool:
        return True

# HTML-like content
<div class="container">
    <div class="controls">
        <button>Click me</button>
    </div>
</div>
"""
    file_path = tmp_path / "test.py"
    file_path.write_text(content)
    return file_path

def test_exact_match(sample_file):
    """Test exact matching of content."""
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
    
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert "def old_function():" not in result
    assert "print(\"Hello\")" not in result
    assert "def another_function():" in result

def test_stripped_match(sample_file):
    """Test matching ignoring whitespace differences."""
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification with different indentation
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Delete
            old_lines:
                .<div class="controls">
                .    <button>Click me</button>
                .</div>
    """)
    
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert '<div class="controls">' not in result
    assert '<button>Click me</button>' not in result
    assert '<div class="container">' in result

def test_python_match(sample_file):
    """Test Python-specific matching rules."""
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification with return type hint
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Replace
            old_lines:
                .def method(self) -> bool:
                .    return True
            new_lines:
                .def method(self):
                .    return False
    """)
    
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert 'def method(self):' in result
    assert '    return False' in result
    assert '-> bool' not in result

def test_indent_pattern_match(sample_file):
    """Test matching based on indentation pattern.
    
    This matches blocks that have the same indentation pattern and stripped content,
    regardless of the actual indentation levels."""
    executor = FileOperationExecutor(sample_file.parent)
    
    # Execute modification matching indentation pattern
    executor.execute(f"""
    Modify File
        name: {sample_file}
        - Replace
            old_lines:
                .class MyClass:
                .    def __init__(self):
                .        self.x = 1
            new_lines:
                .class NewClass:
                .    def setup(self):
                .        self.ready = True
    """)
    
    result = Path(executor.target_dir / sample_file.name).read_text()
    assert 'class NewClass:' in result
    assert '    def setup(self):' in result
    assert '        self.ready = True' in result
    assert 'class MyClass:' not in result 