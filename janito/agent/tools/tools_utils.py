def display_path(path):
    import os

    if os.path.isabs(path):
        return path
    return os.path.relpath(path)


def pluralize(word: str, count: int) -> str:
    """Return the pluralized form of word if count != 1, unless word already ends with 's'."""
    if count == 1 or word.endswith("s"):
        return word
    return word + "s"
