import pytest
from pathlib import Path
from janito.contentchange import (
    parse_block_changes,
    validate_python_syntax,
    get_file_type,
    format_parsed_changes
)

def test_parse_block_changes():
    """Test parsing content blocks with changes"""
    content = """## abc123 test.py begin "Add test function" ##
def test_function():
    assert True
## abc123 test.py end ##

## abc123 README.md begin "Update docs" ##
# Test Project
Updated content
## abc123 README.md end ##"""

    changes = parse_block_changes(content)
    
    assert len(changes) == 2
    assert Path("test.py") in changes
    assert Path("README.md") in changes
    assert "def test_function()" in changes[Path("test.py")]["new_content"]
    assert "Add test function" in changes[Path("test.py")]["description"]

def test_validate_python_syntax():
    """Test Python syntax validation"""
    # Valid syntax
    valid_code = "def test():\n    return True"
    is_valid, error = validate_python_syntax(valid_code, Path("test.py"))
    assert is_valid
    assert error == ""
    
    # Invalid syntax
    invalid_code = "def test(:\n    return True"
    is_valid, error = validate_python_syntax(invalid_code, Path("test.py"))
    assert not is_valid
    assert "syntax" in error.lower()

def test_get_file_type():
    """Test file type detection"""
    assert get_file_type(Path("test_changes.txt")) == "changes"
    assert get_file_type(Path("test_selected.txt")) == "selected"
    assert get_file_type(Path("test_analysis.txt")) == "analysis"
    assert get_file_type(Path("test_other.txt")) == "unknown"

def test_format_parsed_changes():
    """Test formatting parsed changes"""
    changes = {
        Path("test.py"): {
            "description": "Add test",
            "new_content": "def test(): pass"
        },
        Path("README.md"): {
            "description": "Update docs",
            "new_content": "# Test"
        }
    }
    
    formatted = format_parsed_changes(changes)
    assert "=== test.py ===" in formatted
    assert "Add test" in formatted
    assert "=== README.md ===" in formatted
    assert "Update docs" in formatted