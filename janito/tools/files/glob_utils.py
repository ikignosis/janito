#!/usr/bin/env python3
"""
Glob pattern utilities shared by the file search tools.

Used by FindFiles, SearchText and SearchRegex to match paths against glob
exclusion patterns (the ``exclude`` parameter).
"""

import fnmatch
import os


def matches_any_pattern(path: str, patterns: list[str]) -> bool:
    """
    Check if a path matches any of the given glob patterns.

    Matching is performed against both the full relative path (with '/'
    separators) and the basename, so patterns like '*.py' and
    '*/tests/*.py' both work as expected.

    Args:
        path (str): The relative path to check (OS-normalised).
        patterns (list[str]): List of glob patterns.

    Returns:
        bool: True if any pattern matches.
    """
    # Normalise to forward slashes so patterns are platform-independent
    normalised = path.replace(os.sep, "/")
    basename = os.path.basename(normalised)

    for pat in patterns:
        if fnmatch.fnmatch(normalised, pat) or fnmatch.fnmatch(basename, pat):
            return True
    return False
