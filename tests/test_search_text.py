import os
import tempfile
import pytest
from janito.agent.tools.search_text import SearchTextTool


@pytest.fixture
def sample_text_file():
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("hello world\nthis is a test\nsearch me\nhello again\n")
    yield path
    os.remove(path)


def test_search_text_plain(sample_text_file):
    tool = SearchTextTool()
    result = tool.run(paths=sample_text_file, pattern="hello")
    assert "hello world" in result
    assert "hello again" in result
    assert "this is a test" not in result


def test_search_text_regex(sample_text_file):
    tool = SearchTextTool()
    result = tool.run(paths=sample_text_file, pattern="h.llo", is_regex=True)
    assert "hello world" in result
    assert "hello again" in result
    assert "search me" not in result
