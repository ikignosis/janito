"""Contract tests for the tool-card header operation summary.

The tool-card header shows a short summary of a tool call's arguments right
after the tool name (e.g. ``ReadFile /etc/hosts (start at line 1, until EOF)``,
``SearchText 'foo' in ./src``). The summary mirrors the parameters each tool
prints via ``report_start`` (the operation target shown in the CLI), so the
header shows the same information the tool announces when it starts.

These tests pin down the frontend wiring:

1. ``chatFormat.js::toolSummary`` builds the summary per tool name from the
   report_start args (with a fallback to the first-argument ``filepath`` chip
   for tools without an entry);
2. ``index.html`` renders it as a ``.tool-path`` span next to the name;
3. ``tools.css`` styles the summary chip distinctly from ``.tool-name``.
"""

from pathlib import Path

from _frontend import render_index_html

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_chat_format_defines_tool_summary_helper():
    """toolSummary is defined and falls back to the filepath chip."""
    js = (FRONTEND / "js" / "chatFormat.js").read_text(encoding="utf-8")
    assert "toolSummary(name, args) {" in js
    # Unknown tools fall back to the first-argument "filepath" chip.
    assert "return this.toolPath(args);" in js


def test_tool_summary_mirrors_report_start_args():
    """The summary table covers the args each tool prints via report_start."""
    js = (FRONTEND / "js" / "chatFormat.js").read_text(encoding="utf-8")
    # ReadFile: filepath + line range (start_line / max_lines) or head/tail
    assert "case 'ReadFile':" in js
    assert "args.max_lines" in js
    # MoveFile: source -> destination
    assert "case 'MoveFile':" in js
    assert "args.destination" in js
    # SearchText / SearchRegex: query/pattern + target paths
    assert "case 'SearchText':" in js
    assert "case 'SearchRegex':" in js
    assert "args.query" in js
    # FindFiles: path list + size/time criteria
    assert "case 'FindFiles':" in js
    assert "args.min_bytes" in js
    # Gmail folders, OneDrive paths, net/system targets
    assert "case 'ReadEmails':" in js
    assert "args.folder" in js
    assert "case 'CreateOneDriveFolder':" in js
    assert "case 'OpenBrowser':" in js
    assert "case 'WebSearch':" in js


def test_index_html_renders_summary_next_to_name():
    """The tool-card header shows the summary after the tool name."""
    html = render_index_html()
    assert "toolSummary(part.tool.name, part.tool.args)" in html
    assert 'class="tool-path"' in html
    # The summary span sits immediately after the tool-name span.
    name_pos = html.index('class="tool-name" x-text="part.tool.name"')
    assert html.index('class="tool-path"', name_pos) > name_pos


def test_tools_css_styles_summary_chip():
    """The summary chip is visually distinct from the bold tool name."""
    css = (FRONTEND / "css" / "tools.css").read_text(encoding="utf-8")
    assert ".tool-path {" in css
    # Distinct style: mono font, muted colour, chip-like background/border.
    assert "font-family: var(--font-mono)" in css
    assert "color: var(--text-muted)" in css
    assert "text-overflow: ellipsis" in css
