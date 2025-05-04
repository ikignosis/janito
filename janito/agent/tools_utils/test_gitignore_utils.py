import os
import tempfile
import shutil
import pytest
from janito.agent.tools_utils.gitignore_utils import GitignoreFilter


def test_gitignore_filter_basic(tmp_path):
    # Create a .gitignore file
    gitignore_content = """
ignored_file.txt
ignored_dir/
*.log
"""
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(gitignore_content)

    # Create files and directories
    (tmp_path / "ignored_file.txt").write_text("should be ignored")
    (tmp_path / "not_ignored.txt").write_text("should not be ignored")
    (tmp_path / "ignored_dir").mkdir()
    (tmp_path / "ignored_dir" / "file.txt").write_text("should be ignored")
    (tmp_path / "not_ignored_dir").mkdir()
    (tmp_path / "not_ignored_dir" / "file.txt").write_text("should not be ignored")
    (tmp_path / "file.log").write_text("should be ignored")

    gi = GitignoreFilter(str(gitignore_path))

    assert gi.is_ignored(str(tmp_path / "ignored_file.txt"))
    assert not gi.is_ignored(str(tmp_path / "not_ignored.txt"))
    # Directory itself is not ignored, only its contents
    assert not gi.is_ignored(str(tmp_path / "ignored_dir"))
    assert gi.is_ignored(str(tmp_path / "ignored_dir" / "file.txt"))
    assert not gi.is_ignored(str(tmp_path / "not_ignored_dir"))
    assert not gi.is_ignored(str(tmp_path / "not_ignored_dir" / "file.txt"))
    assert gi.is_ignored(str(tmp_path / "file.log"))

    # Test filter_ignored
    dirs = ["ignored_dir", "not_ignored_dir"]
    files = ["ignored_file.txt", "not_ignored.txt", "file.log"]
    filtered_dirs, filtered_files = gi.filter_ignored(str(tmp_path), dirs, files)
    assert "ignored_dir" not in filtered_dirs
    assert "not_ignored_dir" in filtered_dirs
    assert "ignored_file.txt" not in filtered_files
    assert "file.log" not in filtered_files
    assert "not_ignored.txt" in filtered_files
