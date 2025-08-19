"""
Path utilities for handling tilde expansion and other path operations.
"""

import os
from pathlib import Path


def expand_path(path: str) -> str:
    """
    Expand a path, handling tilde (~) expansion for user home directory.

    Args:
        path (str): The path to expand.

    Returns:
        str: The expanded absolute path.
    """
    if not path:
        return path

    # Handle tilde expansion
    expanded = os.path.expanduser(path)

    # Convert to absolute path
    return os.path.abspath(expanded)


def normalize_path(path: str) -> str:
    """
    Normalize a path by expanding tilde and resolving any relative paths.

    Args:
        path (str): The path to normalize.

    Returns:
        str: The normalized absolute path.
    """
    return expand_path(path)
