"""Contract tests for the tool-card filepath display.

Tools whose *first* argument is ``filepath`` (ReadFile, WriteFile, ...)
show that path right after the tool name in the tool-card header, styled
differently from the name. These tests pin down the frontend wiring:

1. ``chatFormat.js::toolPath`` extracts the path only when the first key of
   the (ordered) arguments is ``filepath`` and its value is a non-empty
   string (mirroring the backend tracker in ``janito/tooling/used_files.py``);
2. ``index.html`` renders it as a ``.tool-path`` span next to the name;
3. ``tools.css`` styles the path chip distinctly from ``.tool-name``.
"""

from pathlib import Path

from _frontend import render_index_html

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_chat_format_defines_tool_path_helper():
    """toolPath returns the path only for a first filepath argument."""
    js = (FRONTEND / "js" / "chatFormat.js").read_text(encoding="utf-8")
    assert "toolPath(args) {" in js
    # First key of the ordered args must be "filepath" ...
    assert "keys[0] !== 'filepath'" in js
    # ... and its value must be a non-empty string.
    assert "typeof path === 'string' && path" in js


def test_index_html_renders_tool_path_next_to_name():
    """The tool-card header shows the operation summary after the tool name.

    The header calls ``toolSummary`` (which falls back to ``toolPath`` for
    tools without an entry); the summary span sits right after the name.
    """
    html = render_index_html()
    assert "toolSummary(part.tool.name, part.tool.args)" in html
    assert 'class="tool-path"' in html
    # The summary span sits immediately after the tool-name span.
    name_pos = html.index('class="tool-name" x-text="part.tool.name"')
    assert html.index('class="tool-path"', name_pos) > name_pos


def test_tools_css_styles_tool_path_chip():
    """The path chip is visually distinct from the bold tool name."""
    css = (FRONTEND / "css" / "tools.css").read_text(encoding="utf-8")
    assert ".tool-path {" in css
    # Distinct style: mono font, muted colour, chip-like background/border.
    assert "font-family: var(--font-mono)" in css
    assert "color: var(--text-muted)" in css
    assert "text-overflow: ellipsis" in css
