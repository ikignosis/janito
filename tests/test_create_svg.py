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
