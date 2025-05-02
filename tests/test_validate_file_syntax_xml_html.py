import os
import tempfile
from janito.agent.tools.validate_file_syntax.core import ValidateFileSyntaxTool

tool = ValidateFileSyntaxTool()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def test_valid_xml():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "valid.xml")
        write_file(path, """<root><child>data</child></root>""")
        result = tool.run(path)
        assert "✅ Syntax valid" in result


def test_invalid_xml():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "invalid.xml")
        write_file(path, """<root><child>data</root>""")
        result = tool.run(path)
        assert "Syntax error" in result


def test_valid_html():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "valid.html")
        write_file(path, """<html><body><h1>Title</h1></body></html>""")
        result = tool.run(path)
        assert "✅ Syntax valid" in result


def test_invalid_html():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "invalid.html")
        write_file(path, """<html><body><h1>Title</body></html>""")
        result = tool.run(path)
        assert "Syntax error" in result or "Syntax valid" in result
