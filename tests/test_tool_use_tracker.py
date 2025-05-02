from janito.agent.tool_use_tracker import ToolUseTracker
from janito.agent.tools.create_file import CreateFileTool
from janito.agent.tools.replace_file import ReplaceFileTool


def test_tool_use_tracker_record_and_query():
    tracker = ToolUseTracker.instance()
    tracker._history.clear()  # Reset for test
    tracker.record(
        "get_lines", {"file_path": "foo.txt", "from_line": None, "to_line": None}
    )
    tracker.record(
        "create_file", {"file_path": "foo.txt", "content": "abc", "overwrite": True}
    )
    assert tracker.get_history()[0]["tool"] == "get_lines"
    ops = tracker.get_operations_on_file("foo.txt")
    assert any(op["tool"] == "get_lines" for op in ops)
    assert tracker.file_fully_read("foo.txt")


def test_create_file_refuses_overwrite_without_full_read(tmp_path):
    tracker = ToolUseTracker.instance()
    tracker._history.clear()  # Reset for test
    file_path = tmp_path / "test.txt"
    file_path.write_text("original content")
    tool = CreateFileTool()
    # Try to overwrite without reading
    result = tool.run(str(file_path), "new content")
    assert "cannot create file: file already exists" in result.lower()
    # Simulate full read
    tracker.record(
        "get_lines", {"file_path": str(file_path), "from_line": None, "to_line": None}
    )
    # Now use ReplaceFileTool to overwrite
    replace_tool = ReplaceFileTool()
    result2 = replace_tool.run(str(file_path), "new content")
    assert "replaced file" in result2.lower()
    assert file_path.read_text() == "new content"
