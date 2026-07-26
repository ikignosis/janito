#!/usr/bin/env python3
"""
Open Browser Tool - Opens a URL in the system's default web browser.

This tool uses Python's webbrowser module to launch the system browser
with the given URL.

Note: This tool requires the progress reporting system from the tooling package.
For direct execution, use: python -m janito.tools.system.open_browser [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import json
import webbrowser
from typing import Any

from ...tooling import BaseTool
from ..decorator import tool


@tool(permissions="x")
class OpenBrowser(BaseTool):
    """
    Tool for opening a URL in the system's default web browser.

    Args:
        url (str): The URL to open in the browser.
    """

    def run(self, url: str) -> dict[str, Any]:
        """
        Open the given URL in the system's default web browser.

        Args:
            url (str): The URL to open in the browser.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if the browser was launched
                - 'url': the URL that was opened
                - 'error': error message (only present if success is False)
        """
        try:
            if not url or not url.strip():
                self.report_error("URL must not be empty")
                return {
                    "success": False,
                    "error": "URL must not be empty",
                    "url": url,
                }

            url = url.strip()

            self.report_start(f"🌍 Opening browser: {url}", end="")

            opened = webbrowser.open(url)

            if opened:
                self.report_result("Browser opened successfully")
                return {
                    "success": True,
                    "url": url,
                }
            else:
                self.report_error("Failed to open browser (no suitable browser found)")
                return {
                    "success": False,
                    "error": "No suitable browser found or browser could not be opened",
                    "url": url,
                }

        except Exception as e:
            self.report_error(f"Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
            }


# ── CLI testing harness ─────────────────────────────────────────────
def main():
    """Command line interface for testing the OpenBrowser tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Open a URL in the system's default web browser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://www.example.com"
  %(prog)s "https://github.com" --json
        """,
    )

    parser.add_argument("url", help="URL to open in the browser")
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )

    args = parser.parse_args()

    result = OpenBrowser().run(url=args.url)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"  ✅ Opened: {result['url']}")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
