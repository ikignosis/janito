import pytest
from pathlib import Path
from janito.fileparser import validate_file_path, validate_file_content

def test_validate_file_path():
    # Valid paths
    assert validate_file_path(Path("test.py")) == (True, "")
    assert validate_file_path(Path("folder/test.py")) == (True, "")
    
    # Invalid paths
    assert validate_file_path(Path("/absolute/path.py"))[0] == False
    assert validate_file_path(Path("../escape.py"))[0] == False
    assert validate_file_path(Path("test?.py"))[0] == False
    assert validate_file_path(Path("test*.py"))[0] == False

def test_validate_file_content():
    # Valid content
    assert validate_file_content("print('hello')") == (True, "")
    assert validate_file_content("# Empty file with comment\n") == (True, "")
    
    # Invalid content
    assert validate_file_content("")[0] == False
    
    # Test large content
    large_content = "x" * (1024 * 1024 + 1)  # Slightly over 1MB
    assert validate_file_content(large_content)[0] == False
