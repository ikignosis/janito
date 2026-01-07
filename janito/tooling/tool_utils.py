"""
Utility functions for the janito project.
Add your shared helper functions here.
"""

import os
import urllib.parse


def example_utility_function(x):
    """A simple example utility function."""
    return f"Processed: {x}"


def display_path(path):
    """
    Returns a display-friendly path. Injects an ANSI hyperlink to a local web file viewer using a hardcoded port.
    Args:
        path (str): Path to display.
    Returns:
        str: Display path, as an ANSI hyperlink.
    """

    port = 8088
    if os.path.isabs(path):
        cwd = os.path.abspath(os.getcwd())
        abs_path = os.path.abspath(path)
        # Check if the absolute path is within the current working directory
        if abs_path.startswith(cwd + os.sep):
            disp = os.path.relpath(abs_path, cwd)
        else:
            disp = path
    else:
        disp = os.path.relpath(path)
    # URL injection removed; just return display path
    return disp


def pluralize(word: str, count: int) -> str:
    """Return the pluralized form of word if count != 1, unless word already ends with 's'."""
    if count == 1 or word.endswith("s"):
        return word
    return word + "s"
