"""
Janito Web tools package.

This package provides tools that are only useful in web mode (``--web``).
They produce no side-effects on the backend; instead their results are
rendered inline on the web frontend's content cards.

Currently provides:
    - CreateSVG: render an SVG graphic inline in the chat UI.
"""

from .create_svg import CreateSVG

__all__ = ["CreateSVG"]
