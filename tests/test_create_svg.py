"""
Tests for the CreateSVG tool (inline SVG rendering for the web UI).

The tool itself is a pure echo: it returns the SVG markup unchanged together
with the requested display size (``view_width`` / ``view_height``, default
500x500) so the web frontend can render the graphic at that size.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to allow importing the package directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from janito.tools.janitoweb.create_svg import CreateSVG

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'


def test_default_view_size_is_500x500():
    """The tool defaults to a 500x500 display size when not specified."""
    result = CreateSVG().run(svg_text=SVG)
    assert result["success"] is True
    assert result["content_type"] == "svg"
    assert result["svg_text"] == SVG
    assert result["view_width"] == 500
    assert result["view_height"] == 500


def test_custom_view_size_is_echoed():
    """Explicit view_width/view_height are echoed back in the result."""
    result = CreateSVG().run(svg_text=SVG, view_width=800, view_height=600)
    assert result["success"] is True
    assert result["view_width"] == 800
    assert result["view_height"] == 600


def test_schema_exposes_optional_integer_size_params():
    """The tool schema exposes view_width/view_height as optional integers.

    Because both parameters have default values, they must NOT be listed in
    the schema's ``required`` list, so the model can omit them.
    """
    from janito.tooling.schema import get_function_schema
    from janito.tools import discover_toolsets

    tools = discover_toolsets(["janitoweb"])
    schema = get_function_schema(tools["CreateSVG"])

    params = schema["function"]["parameters"]
    props = params["properties"]
    assert props["view_width"]["type"] == "integer"
    assert props["view_height"]["type"] == "integer"
    assert "view_width" not in params["required"]
    assert "view_height" not in params["required"]
    # The SVG text itself remains required.
    assert "svg_text" in params["required"]
