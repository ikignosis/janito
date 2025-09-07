import os
import pytest
from .read_file import read_file, view_file, read_files


def test_read_file_single_with_range(tmp_path):
    """Test reading a single file with line range"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")

    result = read_file(str(test_file), from_line=2, to_line=4)

    assert "--- File: " in result
    assert "Lines: 2-4" in result
    assert "Line 2" in result
    assert "Line 3" in result
    assert "Line 4" in result
    assert "Line 1" not in result
    assert "Line 5" not in result


def test_read_file_single_without_range(tmp_path):
    """Test reading a single file without line range"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")

    result = read_file(str(test_file))

    assert "--- File: " in result
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result


def test_read_file_multiple_files(tmp_path):
    """Test reading multiple files"""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Content 1\n")
    file2.write_text("Content 2\n")

    result = read_file([str(file1), str(file2)])

    assert "--- File: " in result
    assert str(file1.name) in result
    assert str(file2.name) in result
    assert "Content 1" in result
    assert "Content 2" in result


def test_read_file_missing_file(tmp_path):
    """Test reading a missing file"""
    missing_file = tmp_path / "missing.txt"

    result = read_file([str(missing_file)])

    assert "Error reading file" in result
    assert str(missing_file.name) in result


def test_view_file_basic(tmp_path):
    """Test view_file function directly"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")

    result = view_file(str(test_file))

    assert "--- File: " in result
    assert "All lines" in result
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result


def test_read_files_basic(tmp_path):
    """Test read_files function directly"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content\n")

    result = read_files([str(test_file)])

    assert "--- File: " in result
    assert "Test content" in result
