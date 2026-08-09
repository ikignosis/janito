"""Contract tests for the native Responses-API image content card.

The web Responses runner (``janito/web/backend/agent/responses.py``) captures
the built-in ``image_generation`` tool's results -- the model generates an
image directly in the response stream, no function-call round-trip -- saves
each PNG to a temp file, and emits an ``image`` event whose ``path`` points
at it. These tests pin down the frontend wiring that renders that event as a
content card and rebuilds the card from stored history:

1. ``chatEvents.js`` handles the ``image`` event and pushes an ``image`` part;
2. ``chatHistory.js`` reconstructs image parts from the assistant message's
   ``images`` list (persisted by the backend on the turn's assistant message);
3. ``index.html`` renders the ``image`` part through ``imageUrl`` (the same
   card used by the CreateImage tool).
"""

from pathlib import Path

from _frontend import render_index_html

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_chat_events_handles_image_event():
    """The live-stream handler turns an ``image`` event into an image part."""
    js = (FRONTEND / "js" / "chatEvents.js").read_text(encoding="utf-8")
    assert "image(c) {" in js
    assert "kind: 'image', path: c.event.path" in js


def test_chat_history_reconstructs_image_parts():
    """History replay rebuilds image cards from the assistant message's
    ``images`` list."""
    js = (FRONTEND / "js" / "chatHistory.js").read_text(encoding="utf-8")
    assert "msg.images" in js
    assert "kind: 'image', path: img.path" in js


def test_index_html_renders_image_part():
    """The image part kind is rendered through imageUrl (shared card)."""
    html = render_index_html()
    assert "part.kind === 'image'" in html
    assert "imageUrl(part.path)" in html
