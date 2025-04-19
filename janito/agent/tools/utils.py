import os


def expand_path(path: str) -> str:
    """
    If ~ is present in the path, expands it to the user's home directory.
    Otherwise, returns the path unchanged.
    """
    if "~" in path:
        return os.path.expanduser(path)
    return path


def display_path(original_path: str, expanded_path: str) -> str:
    """
    Returns a user-friendly path for display:
    - If the original path is relative, return it as-is.
    - If the original path starts with ~, keep it as ~.
    - Otherwise, if the expanded path is under the home directory, replace the home dir with ~.
    - Else, show the expanded path.
    """
    # Detect relative path (POSIX or Windows)
    if not (original_path.startswith("/") or original_path.startswith("~") or (os.name == "nt" and len(original_path) > 1 and original_path[1] == ":")):
        return original_path
    home = os.path.expanduser("~")
    if original_path.startswith("~"):
        return original_path
    if expanded_path.startswith(home):
        return "~" + expanded_path[len(home):]
    return expanded_path
