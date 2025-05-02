import os
from janito.agent.tools.validate_file_syntax.core import ValidateFileSyntaxTool


def write_temp_file(content, filename="temp_test.md"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def remove_temp_file(filename):
    try:
        os.remove(filename)
    except Exception:
        pass


def test_valid_markdown():
    valid_md = """# Header 1\n\n- Item 1\n- Item 2\n\nSome `inline code`.\n\n```
block code
```\n\n[Link](https://example.com)\n"""
    filename = write_temp_file(valid_md)
    tool = ValidateFileSyntaxTool()
    result = tool.run(filename)
    remove_temp_file(filename)
    assert "✅" in result


def test_invalid_markdown():
    invalid_md = """#Header1\n\n-Item 1\n\nSome `inline code.\n\n```
block code\n\n[Link](https://example.com\n"""
    filename = write_temp_file(invalid_md)
    tool = ValidateFileSyntaxTool()
    result = tool.run(filename)
    remove_temp_file(filename)
    assert "Warning" in result and "Markdown syntax issues" in result


def test_unclosed_code_block():
    md = """# Header\n\n```
code block\n"""
    filename = write_temp_file(md)
    tool = ValidateFileSyntaxTool()
    result = tool.run(filename)
    remove_temp_file(filename)
    assert "Unclosed code block" in result


def test_unclosed_inline_code():
    md = "Some `inline code."
    filename = write_temp_file(md)
    tool = ValidateFileSyntaxTool()
    result = tool.run(filename)
    remove_temp_file(filename)
    assert "Unclosed inline code" in result


def test_list_item_missing_space():
    md = "-Item 1\n*Item 2\n+Item 3"
    filename = write_temp_file(md)
    tool = ValidateFileSyntaxTool()
    result = tool.run(filename)
    remove_temp_file(filename)
    assert "List item missing space after bullet" in result
