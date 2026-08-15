#!/usr/bin/env python3
"""
Gitignore utilities - Shared helpers for loading and matching .gitignore patterns.

Used by search tools (SearchText, SearchRegex, etc.) to optionally respect
.gitignore patterns when traversing directories, and to always respect
.janitoignore patterns.
"""

import os

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern


def load_ignore_spec(directory: str, filename: str, extra_patterns=None):
    """
    Load ignore patterns from the specified file in the given directory.

    Uses the 'pathspec' library for proper gitignore parsing.

    Args:
        directory (str): The directory to look for the ignore file
        filename (str): The ignore file name (e.g. ".gitignore", ".janitoignore")
        extra_patterns (list[str], optional): Additional pattern lines to
            always include in the spec, after the file contents.

    Returns:
        A PathSpec object, or None if the ignore file does not exist.
    """
    ignore_path = os.path.join(directory, filename)

    if not os.path.exists(ignore_path):
        return None

    with open(ignore_path) as f:
        patterns = f.readlines()

    if extra_patterns:
        patterns.extend(extra_patterns)

    return PathSpec.from_lines(GitWildMatchPattern, patterns)


def load_gitignore_spec(directory: str):
    """
    Load .gitignore patterns from the specified directory.

    Args:
        directory (str): The directory to look for .gitignore

    Returns:
        A PathSpec object, or None if no .gitignore file exists.
    """
    return load_ignore_spec(directory, ".gitignore")


def load_janitoignore_spec(directory: str):
    """
    Load .janitoignore patterns from the specified directory.

    .janitoignore is always respected by the file tools, regardless of the
    respect_gitignore setting. The .janitoignore file itself is automatically
    added to the ignore list, so it never appears in listings or search
    results.

    Args:
        directory (str): The directory to look for .janitoignore

    Returns:
        A PathSpec object, or None if no .janitoignore file exists.
    """
    return load_ignore_spec(
        directory, ".janitoignore", extra_patterns=[".janitoignore\n"]
    )


def is_ignored_by_gitignore(
    rel_path: str, gitignore_spec, is_dir: bool = False
) -> bool:
    """
    Check if a path is ignored by ignore-file patterns.

    Args:
        rel_path (str): Relative path to check
        gitignore_spec: The PathSpec object
        is_dir (bool): Whether the path is a directory. Directory-only
            ignore patterns (those ending with '/') only match when this
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
