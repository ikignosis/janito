import os
from janito.agent.tools.gitignore_utils import filter_ignored


def display_path(path):
    if os.path.isabs(path):
        return path
    return os.path.relpath(path)


def pluralize(word: str, count: int) -> str:
    """Return the pluralized form of word if count != 1, unless word already ends with 's'."""
    if count == 1 or word.endswith("s"):
        return word
    return word + "s"


def find_files_with_extensions(directories, extensions, recursive=True):
    """
    Find files in given directories with specified extensions, respecting .gitignore.

    Args:
        directories (list[str]): Directories to search.
        extensions (list[str]): File extensions to include (e.g., ['.py', '.md']).
        recursive (bool): Whether to search subdirectories.
    Returns:
        list[str]: List of matching file paths.
    """
    output = []
    for directory in directories:
        for root, dirs, files in os.walk(directory):
            rel_path = os.path.relpath(root, directory)
            depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
            if not recursive and depth > 0:
                break
            dirs, files = filter_ignored(root, dirs, files)
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in extensions):
                    output.append(os.path.join(root, filename))
    return output
