"""Contract tests for the web SVG content card (issue #27).

The CreateSVG tool (``janito/tools/janitoweb/create_svg.py``) returns the SVG
markup together with a requested display size (``view_width`` / ``view_height``,
default 500x500). These tests pin down the frontend wiring that makes the chat
card respect that size:

1. ``chatEvents.js`` stores the result's view_width/view_height on the SVG part;
2. ``chatHistory.js`` reconstructs them when replaying a stored session;
3. ``index.html`` passes them into ``sanitizeSvg``;
4. ``chatFormat.js::sanitizeSvg`` stamps them onto the root ``<svg>`` element
   as an inline style, so the graphic renders at exactly the requested size.
"""

from pathlib import Path

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_chat_events_stores_svg_view_size():
    """The live-stream handler keeps view_width/view_height on the svg part."""
    js = (FRONTEND / "js" / "chatEvents.js").read_text(encoding="utf-8")
    assert "view_width: c.event.result.view_width" in js
    assert "view_height: c.event.result.view_height" in js


def test_chat_history_reconstructs_svg_view_size():
    """History replay restores view_width/view_height from the stored result."""
    js = (FRONTEND / "js" / "chatHistory.js").read_text(encoding="utf-8")
    assert "view_width: result.view_width" in js
    assert "view_height: result.view_height" in js


def test_index_html_passes_svg_view_size_to_sanitizer():
    """The svg-card template forwards the size params to sanitizeSvg."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert "sanitizeSvg(part.svg, part.view_width, part.view_height)" in html


def test_chat_format_stamps_svg_view_size():
    """sanitizeSvg accepts width/height and stamps them as an inline style."""
    js = (FRONTEND / "js" / "chatFormat.js").read_text(encoding="utf-8")
    assert "sanitizeSvg(svgText, viewWidth, viewHeight)" in js
    assert "width:${viewWidth}px" in js
    assert "height:${viewHeight}px" in js
    # The inline style is applied to the root <svg> element.
    assert "<svg${cleaned} style=" in js
