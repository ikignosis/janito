import os
import urllib.parse
from janito.agent.runtime_config import runtime_config


def display_path(path):
    """
    Returns a display-friendly path. If runtime_config['termweb_port'] is set, injects an ANSI hyperlink to the local web file viewer.
    Args:
        path (str): Path to display.
    Returns:
        str: Display path, optionally as an ANSI hyperlink.
    """
    if os.path.isabs(path):
        disp = path
    else:
        disp = os.path.relpath(path)
    port = runtime_config.get("termweb_port")
    if port:
        url = f"http://localhost:{port}/?path={urllib.parse.quote(path)}"
        # Use Rich markup for hyperlinks
        return f"[link={url}]{disp}[/link]"
    return disp


def pluralize(word: str, count: int) -> str:
    """Return the pluralized form of word if count != 1, unless word already ends with 's'."""
    if count == 1 or word.endswith("s"):
        return word
    return word + "s"


def find_files_with_extensions(directories, extensions, max_depth=0):
    """
    Find files in given directories with specified extensions, respecting .gitignore.

    Args:
        directories (list[str]): Directories to search.
        extensions (list[str]): File extensions to include (e.g., ['.py', '.md']).
        max_depth (int, optional): Maximum directory depth to search. If 0, unlimited.
    Returns:
        list[str]: List of matching file paths.
    """
    from janito.agent.tools_utils.gitignore_utils import filter_ignored

    output = []
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            rel_path = os.path.relpath(root, directory)
            depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
            if max_depth > 0 and depth > max_depth:
                continue
            dirs, files = filter_ignored(root, dirs, files)
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in extensions):
                    output.append(os.path.join(root, filename))
    return output
