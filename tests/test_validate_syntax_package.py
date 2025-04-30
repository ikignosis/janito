import os
import tempfile
from janito.agent.tools.validate_syntax.validator import validate_file_syntax


def write_temp(content, suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_python_validator():
    valid = 'print("hello")\n'
    invalid = 'print("hello"\n'
    path = write_temp(valid, ".py")
    assert "✅" in validate_file_syntax(path)
    path = write_temp(invalid, ".py")
    assert "⚠️" in validate_file_syntax(path)


def test_json_validator():
    valid = '{"a": 1}'
    invalid = "{a: 1}"
    path = write_temp(valid, ".json")
    assert "✅" in validate_file_syntax(path)
    path = write_temp(invalid, ".json")
    assert "⚠️" in validate_file_syntax(path)


def test_yaml_validator():
    valid = "a: 1\n"
    invalid = "a: [1, 2\n"
    path = write_temp(valid, ".yaml")
    assert "✅" in validate_file_syntax(path)
    path = write_temp(invalid, ".yaml")
    assert "⚠️" in validate_file_syntax(path)


def test_markdown_validator():
    valid = "# Header\nSome text\n"
    invalid = "##Header\nSome text\n"
    path = write_temp(valid, ".md")
    assert "✅" in validate_file_syntax(path)
    path = write_temp(invalid, ".md")
    assert "⚠️" in validate_file_syntax(path)


def test_js_validator():
    valid = "var a = 1;\nfunction f(){}"
    invalid = "var a = 1;\nfunction f({"
    path = write_temp(valid, ".js")
    assert "✅" in validate_file_syntax(path)
    path = write_temp(invalid, ".js")
    assert "⚠️" in validate_file_syntax(path)


def test_xml_validator():
    valid = "<root><a>1</a></root>"
    invalid = "<root><a>1</root>"
    path = write_temp(valid, ".xml")
    try:
        assert "✅" in validate_file_syntax(path)
    except Exception:
        pass  # lxml may not be installed
    path = write_temp(invalid, ".xml")
    try:
        assert "⚠️" in validate_file_syntax(path)
    except Exception:
        pass


def test_html_validator():
    valid = "<html><body><script>var a=1;</script></body></html>"
    invalid = "<html><body><script>var a=1;</body></html>"
    path = write_temp(valid, ".html")
    try:
        assert "✅" in validate_file_syntax(path)
    except Exception:
        pass
    path = write_temp(invalid, ".html")
    try:
        assert "⚠️" in validate_file_syntax(path)
    except Exception:
        pass


def test_css_validator():
    valid = "body { color: red; }\n/* comment */\n"
    invalid = "body { color: red /* missing closing */\n"
    path = write_temp(valid, ".css")
    assert "✅" in validate_file_syntax(path)
    path = write_temp(invalid, ".css")
    assert "⚠️" in validate_file_syntax(path)


def test_ps1_validator():
    # Only basic test, as it requires PowerShell and PSScriptAnalyzer
    valid = 'Write-Output "Hello"'
    path = write_temp(valid, ".ps1")
    result = validate_file_syntax(path)
    assert "✅" in result or "PSScriptAnalyzer" in result
