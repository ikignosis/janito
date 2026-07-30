#!/usr/bin/env python3
"""
Gitignore utilities - Shared helpers for loading and matching .gitignore patterns.

Used by search tools (SearchText, SearchRegex, etc.) to optionally respect
.gitignore patterns when traversing directories.
"""

import os

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern


def load_gitignore_spec(directory: str):
    """
    Load .gitignore patterns from the specified directory.

    Uses the 'pathspec' library for proper gitignore parsing.

    Args:
        directory (str): The directory to look for .gitignore

    Returns:
        A PathSpec object, or None if no .gitignore file exists.
    """
    gitignore_path = os.path.join(directory, ".gitignore")

    if not os.path.exists(gitignore_path):
        return None

    with open(gitignore_path, "r") as f:
        patterns = f.readlines()

    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def is_ignored_by_gitignore(
    rel_path: str, gitignore_spec, is_dir: bool = False
) -> bool:
    """
    Check if a path is ignored by gitignore patterns.

    Args:
        rel_path (str): Relative path to check
        gitignore_spec: The PathSpec object
        is_dir (bool): Whether the path is a directory. Directory-only
            gitignore patterns (those ending with '/') only match when this
            is True.

    Returns:
        bool: True if the path should be ignored
    """
    if gitignore_spec is None:
        return False

    # Normalize path separators for matching
    normalized_path = rel_path.replace(os.sep, "/")
    if is_dir and not normalized_path.endswith("/"):
        normalized_path += "/"

    return gitignore_spec.match_file(normalized_path)
