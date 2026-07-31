#!/usr/bin/env python3
"""
Create SVG Tool - A class-based tool for rendering SVG graphics inline in the
web frontend.

This tool does nothing on the backend side — it simply returns the SVG text
back to the caller. When janito runs in ``--web`` mode, the frontend detects
the ``CreateSVG`` tool result and renders the ``svg_text`` inline on a
content card, sized according to the ``view_width`` / ``view_height``
parameters.

For AI function calling, use through the tool registry (tooling.tools_registry).
"""

from typing import Any

from ...tooling import BaseTool
from ...tooling.decorator import tool

# Default display size (in pixels) for the rendered SVG. The frontend uses
# these to size the inline graphic when the model does not request a size.
_DEFAULT_VIEW_WIDTH = 500
_DEFAULT_VIEW_HEIGHT = 500


@tool()
class CreateSVG(BaseTool):
    """
    Create an SVG graphic to be displayed inline in the web UI.

    This tool accepts raw SVG markup and returns it unchanged. The web
    frontend renders the SVG inline on a content card. The tool itself
    performs no side-effects on the backend.

    Use this tool when the user wants to visualise something as an SVG
    graphic — diagrams, charts, icons, illustrations, etc.

    Args:
        svg_text (str): Raw SVG markup (e.g. '<svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>')
        view_width (int): Display width of the SVG in pixels (default 500).
        view_height (int): Display height of the SVG in pixels (default 500).
    """

    def run(
        self,
        svg_text: str,
        view_width: int = _DEFAULT_VIEW_WIDTH,
        view_height: int = _DEFAULT_VIEW_HEIGHT,
    ) -> dict[str, Any]:
        """
        Create an SVG graphic for inline display in the web UI.

        Args:
            svg_text (str): Raw SVG markup (e.g. '<svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>')
            view_width (int): Display width of the SVG in pixels (default 500).
            view_height (int): Display height of the SVG in pixels (default 500).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if operation succeeded
                - 'svg_text': the SVG markup (echoed back for frontend rendering)
                - 'content_type': 'svg' (hint for the frontend renderer)
                - 'view_width': requested display width in pixels
                - 'view_height': requested display height in pixels
        """
        self.report_result("SVG created for inline display")
        return {
            "success": True,
            "svg_text": svg_text,
            "content_type": "svg",
            "view_width": view_width,
            "view_height": view_height,
        }


# ── CLI testing harness ─────────────────────────────────────────────────────
def main():
    """Command line interface for testing the CreateSVG tool."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Create an SVG graphic for inline display in the web UI"
    )
    parser.add_argument("svg_text", help="Raw SVG markup to echo back")
    parser.add_argument(
        "--view-width",
        type=int,
        default=_DEFAULT_VIEW_WIDTH,
        help="Display width in pixels (default: %(default)s)",
    )
    parser.add_argument(
        "--view-height",
        type=int,
        default=_DEFAULT_VIEW_HEIGHT,
        help="Display height in pixels (default: %(default)s)",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    args = parser.parse_args()

    result = CreateSVG().run(
        svg_text=args.svg_text,
        view_width=args.view_width,
        view_height=args.view_height,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"✅ SVG created ({result['view_width']}x{result['view_height']})")
        print(result["svg_text"])

    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
