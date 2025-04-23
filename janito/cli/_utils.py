import os


def home_shorten(path: str) -> str:
    """If path starts with the user's home directory, replace it with ~."""
    home = os.path.expanduser("~")
    if path and isinstance(path, str) and path.startswith(home):
        return path.replace(home, "~", 1)
    return path
