import pytest
from pathlib import Path
from janito.scan import (
    collect_files_content,
    is_dir_empty,
    preview_scan,
    _scan_paths
)

def test_collect_files_content(mock_files):
    """Test collecting content from files"""
    content = collect_files_content([mock_files])
    
    assert "def test():" in content
    assert "# Test Project" in content
    assert "print('hello')" in content
    assert "<file>" in content
    assert "</file>" in content

def test_is_dir_empty(temp_workdir):
    """Test empty directory detection"""
    assert is_dir_empty(temp_workdir)
    
    # Add a file
    (temp_workdir / "test.txt").write_text("test")
    assert not is_dir_empty(temp_workdir)
    
    # Hidden files should be ignored
    (temp_workdir / ".hidden").write_text("hidden")
    assert not is_dir_empty(temp_workdir)

def test_preview_scan(mock_files, capsys):
    """Test scan preview functionality"""
    preview_scan([mock_files], mock_files)
    
    captured = capsys.readouterr()
    assert "test.py" in captured.out
    assert "README.md" in captured.out
    assert "src/project/main.py" in captured.out

def test_scan_paths_with_gitignore(mock_files):
    """Test scanning with .gitignore patterns"""
    # Create .gitignore
    gitignore_content = """
    *.pyc
    __pycache__/
    .pytest_cache/
    """
    (mock_files / ".gitignore").write_text(gitignore_content)
    
    # Create files that should be ignored
    ignored_files = [
        mock_files / "test.pyc",
        mock_files / "__pycache__" / "cache.pyc",
        mock_files / ".pytest_cache" / "v" / "cache.pyc"
    ]
    
    # Create the ignored files and directories
    for file_path in ignored_files:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("ignored content")
    
    # Create regular files that should be included
    included_files = [
        mock_files / "test.py",
        mock_files / "README.md",
        mock_files / "src" / "project" / "main.py"
    ]
    
    for file_path in included_files:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("included content")
    
    content_parts, file_items = _scan_paths([mock_files], mock_files)
    content = "\n".join(content_parts)
    
    # Verify ignored files are not in content
    for ignored_file in ignored_files:
        assert f"<path>{ignored_file.relative_to(mock_files)}</path>" not in content
        assert "ignored content" not in content
    
    # Verify included files are in content
    for included_file in included_files:
        assert f"<path>{included_file.relative_to(mock_files)}</path>" in content
        assert "included content" in content
    
    # Verify ignored directories are not in content
    assert "<path>__pycache__</path>" not in content
    assert "<path>.pytest_cache</path>" not in content
    
    # Verify file structure in file_items
    file_items_str = "\n".join(file_items)
    assert "test.pyc" not in file_items_str
    assert "__pycache__" not in file_items_str
    assert ".pytest_cache" not in file_items_str
    assert "test.py" in file_items_str
    assert "README.md" in file_items_str
    assert "src/project/main.py" in file_items_str