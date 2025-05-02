import os
import tempfile
from janito.agent.tools.validate_file_syntax.core import ValidateFileSyntaxTool

tool = ValidateFileSyntaxTool()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def test_valid_python():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "valid.py")
        write_file(path, "def foo():\n    return 42\n")
        result = tool.run(path)
        assert "✅ Syntax valid" in result


def test_invalid_python():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "invalid.py")
        write_file(path, "def foo(:\n    return 42\n")
        result = tool.run(path)
        assert "Syntax error" in result


def test_valid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "valid.json")
        write_file(path, '{"a": 1, "b": 2}')
        result = tool.run(path)
        assert "✅ Syntax valid" in result


def test_invalid_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "invalid.json")
        write_file(path, '{"a": 1, "b": 2,,}')
        result = tool.run(path)
        assert "Syntax error" in result


def test_valid_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "valid.yaml")
        write_file(path, "a: 1\nb: 2\n")
        result = tool.run(path)
        assert "✅ Syntax valid" in result


def test_invalid_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "invalid.yaml")
        write_file(path, "a: 1\nb 2\n")
        result = tool.run(path)
        assert "Syntax error" in result


def test_unsupported_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "file.txt")
        write_file(path, "just some text")
        result = tool.run(path)
        assert "Unsupported file extension" in result
