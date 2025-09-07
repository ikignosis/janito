import os
import pytest
from janito.tools.adapters.local.read_files import ReadFilesTool


@pytest.fixture
def read_files_tool():
    return ReadFilesTool()


def test_read_files_tool(tmp_path, read_files_tool):
    # Create some test files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Hello from file 1!\n")
    file2.write_text("Second file contents.\n")
    missing_file = tmp_path / "missing.txt"

    result = read_files_tool.run(paths=[str(file1), str(file2), str(missing_file)])

    assert "Hello from file 1!" in result
    assert "Second file contents." in result
    assert "not found" in result or "error" in result
    assert str(file1.name) in result
    assert str(file2.name) in result
    assert str(missing_file.name) in result
