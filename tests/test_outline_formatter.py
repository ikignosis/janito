import pytest
from janito.agent.tools_utils.formatting import OutlineFormatter


def test_format_outline_table_empty():
    assert (
        OutlineFormatter.format_outline_table([])
        == "No classes, functions, or variables found."
    )


def test_format_outline_table_basic():
    items = [
        {
            "type": "class",
            "name": "Foo",
            "start": 1,
            "end": 10,
            "parent": "",
            "docstring": "A class.",
        },
        {
            "type": "function",
            "name": "bar",
            "start": 12,
            "end": 15,
            "parent": "Foo",
            "docstring": "Does bar.",
        },
    ]
    result = OutlineFormatter.format_outline_table(items)
    assert "| class   | Foo" in result
    assert "| function | bar" in result
    assert "A class." in result
    assert "Does bar." in result


def test_format_markdown_outline_table_empty():
    assert OutlineFormatter.format_markdown_outline_table([]) == "No headers found."


def test_format_markdown_outline_table_basic():
    items = [
        {"level": 1, "title": "Header 1", "line": 1},
        {"level": 2, "title": "Header 2", "line": 3},
    ]
    result = OutlineFormatter.format_markdown_outline_table(items)
    assert "| 1     | Header 1" in result
    assert "| 2     | Header 2" in result
