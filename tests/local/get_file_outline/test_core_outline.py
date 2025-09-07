import os
import tempfile
import pytest
from janito.tools.adapters.local.get_file_outline.core import GetFileOutlineTool


@pytest.fixture
def outline_tool():
    return GetFileOutlineTool()


@pytest.mark.parametrize(
    "ext,content,expected_type",
    [
        (".py", "def foo():\n    pass\n", "python"),
        (".md", "# Heading 1\nSome text\n## Heading 2\n", "markdown"),
    ],
)
def test_get_file_outline_supported_types(outline_tool, ext, content, expected_type):
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=ext, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = outline_tool.run(tmp_path)
        assert f"({expected_type})" in result
        assert "Outline:" in result
        assert "Error" not in result
    finally:
        os.remove(tmp_path)
