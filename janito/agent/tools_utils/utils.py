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
