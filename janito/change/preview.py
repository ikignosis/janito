from pathlib import Path
import shutil
import tempfile
from typing import List, Set, Tuple
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

from janito.config import config

# Common patterns to ignore during file operations
IGNORE_PATTERNS = (
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '.Python',
    '.pytest_cache',
    '.coverage',
    '.tox',
    '.janito',
    '.git'
)

def setup_preview_directory() -> Path:
    """Creates and sets up preview directory with working directory contents.
    Returns the path to the preview directory."""
    preview_dir = Path(tempfile.mkdtemp())

    # Copy existing files to preview directory if workspace_dir exists
    if config.workspace_dir.exists():
        shutil.copytree(config.workspace_dir, preview_dir, dirs_exist_ok=True,
                       ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))

    return preview_dir

def setup_workspace_dir_preview() -> Path:
    """Sets up preview directory.
    Returns preview directory path."""
    preview_dir = setup_preview_directory()
    return preview_dir