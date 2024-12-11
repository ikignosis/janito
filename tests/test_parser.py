import pytest
from pathlib import Path
from janito.change.parser import CommandParser, FileChange, Modification

def test_empty_input():
    parser = CommandParser()
    assert parser.parse_response("") == []
    assert parser.parse_response("   \n  \n  ") == []

def test_create_file():
    input_text = """
    Create File
        Path: test.py
        Content:
            .def test():.
            .    return True.
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 1
    assert changes[0].operation == "create_file"
    assert changes[0].path == Path("test.py")
    assert changes[0].content == "def test():\n    return True"

def test_replace_file():
    input_text = """
    Replace File
        Path: old.py
        Content:
            .new content.
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 1
    assert changes[0].operation == "replace_file"
    assert changes[0].path == Path("old.py")
    assert changes[0].content == "new content"

def test_remove_file():
    input_text = """
    Remove File
        Path: delete.py
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 1
    assert changes[0].operation == "remove_file"
    assert changes[0].path == Path("delete.py")

def test_rename_file():
    input_text = """
    Rename File
        OldPath: old.py
        NewPath: new.py
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 1
    assert changes[0].operation == "rename_file"
    assert changes[0].path == Path("old.py")
    assert changes[0].new_path == Path("new.py")

def test_modify_file():
    input_text = """
    Modify File
        Path: modify.py
        Modifications:
            Select
                .old_code.
            Replace Selected
                .new_code.
            Select
                .to_delete.
            Delete Selected
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 1
    assert changes[0].operation == "modify_file"
    assert changes[0].path == Path("modify.py")
    assert len(changes[0].modifications) == 2
    
    assert changes[0].modifications[0].search_content == "old_code"
    assert changes[0].modifications[0].replace_content == "new_code"
    assert not changes[0].modifications[0].is_regex
    
    assert changes[0].modifications[1].search_content == "to_delete"
    assert changes[0].modifications[1].replace_content is None

def test_regex_modifications():
    input_text = """
    Modify File
        Path: regex.py
        Modifications:
            SelectRegex
                .def \\w+\\(\\):.
            Replace Selected
                .def new_func():.
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 1
    change = changes[0]
    assert len(change.modifications) == 1
    modificiation = change.modifications[0]
    assert modificiation.is_regex
    assert modificiation.search_content == r"def \w+\(\):"

def test_description_handling():
    input_text = """
    Create File
        Desc: Test description
        Path: desc.py
        Content:
            .content.
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert changes[0].description == "Test description"

def test_multiline_description():
    input_text = """
    Create File
        Desc:
            .Line 1.
            .Line 2.
        Path: desc.py
        Content:
            .content.
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert changes[0].description == "Line 1\nLine 2"

def test_invalid_text_block():
    input_text = """
    Create File
        Path: test.py
        Content:
            .invalid line
    """
    parser = CommandParser()
    with pytest.raises(ValueError, match="Text block line missing trailing dot"):
        parser.parse_response(input_text)

def test_multiple_commands():
    input_text = """
    Create File
        Path: file1.py
        Content:
            .content1.
    
    Remove File
        Path: file2.py
    
    Modify File
        Path: file3.py
        Modifications:
            Select
                .old.
            Replace Selected
                .new.
    """
    parser = CommandParser()
    changes = parser.parse_response(input_text)
    
    assert len(changes) == 3
    assert [c.operation for c in changes] == ["create_file", "remove_file", "modify_file"]
