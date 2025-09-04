"""
Web Tools Plugin

Web scraping, browsing, and URL operations.
"""

from typing import Optional, Dict, List


def open_url(url: str) -> str:
    """Open URLs in default browser"""
    return f"open_url(url='{url}')"


def open_html_in_browser(path: str) -> str:
    """Open local HTML files in browser"""
    return f"open_html_in_browser(path='{path}')"


# Plugin metadata
__plugin_name__ = "web.webtools"
__plugin_description__ = "Web scraping, browsing, and URL operations"
__plugin_tools__ = [open_url, open_html_in_browser]
