import os


def expand_path(path: str) -> str:
    """
    If ~ is present in the path, expands it to the user's home directory.
    Otherwise, returns the path unchanged.
    """
    if "~" in path:
        return os.path.expanduser(path)
    return path


def display_path(path: str) -> str:
    """
    Returns a user-friendly path for display:
    - If the path is relative, return it as-is.
    - If the path starts with ~, keep it as ~.
    - If the path is under the home directory, replace the home dir with ~.
    - Else, show the absolute path.
    """
    if not (
        path.startswith("/")
        or path.startswith("~")
        or (os.name == "nt" and len(path) > 1 and path[1] == ":")
    ):
        return path
    home = os.path.expanduser("~")
    if path.startswith("~"):
        return path
    if path.startswith(home):
        return "~" + path[len(home) :]
    return path
