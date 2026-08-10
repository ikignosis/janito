"""Contract tests for the code-execution tool card display.

When a code-execution tool (RunBashCode, RunPythonCode, RunPowerShellCode)
is called, the submitted ``code`` argument is shown as a code block at the
top of the corresponding tool card, BEFORE the tool actually executes (i.e.
before any live output streams in). These tests pin down the wiring:

1. ``chatFormat.js::isCodeTool`` recognises the code-execution tools;
2. ``index.html`` renders the code block in the tool-card body (guarded on
   ``isCodeTool`` + a present ``args.code``), placed before the live
   progress/output section;
3. ``tools.css`` styles the code block like the output/progress blocks.
"""

from pathlib import Path

from _frontend import render_index_html

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_chat_format_defines_is_code_tool_helper():
    """isCodeTool recognises the code-execution tools."""
    js = (FRONTEND / "js" / "chatFormat.js").read_text(encoding="utf-8")
    assert "isCodeTool(name) {" in js
    # Bash, Python and PowerShell all take a `code` argument.
    assert "RunBashCode" in js
    assert "RunPythonCode" in js
    assert "RunPowerShellCode" in js


def test_index_html_renders_code_block_before_output():
    """The tool-card body shows args.code before the live progress section.

    The block is guarded on the tool being a code-execution tool with a
    non-empty ``args.code``, and sits above the live progress/output loop.
    """
    html = render_index_html()

    # The code block only renders for code tools that carry a `code` arg.
    assert "isCodeTool(part.tool.name) && part.tool.args && part.tool.args.code" in html
    assert 'class="tool-code" x-text="part.tool.args.code"' in html

    # It is placed BEFORE the live progress/output section in the card body.
    code_pos = html.index('class="tool-code" x-text="part.tool.args.code"')
    progress_pos = html.index("Live progress / output")
    assert code_pos < progress_pos


def test_tools_css_styles_code_block():
    """The code block uses the same mono/code styling as the output blocks."""
    css = (FRONTEND / "css" / "tools.css").read_text(encoding="utf-8")
    assert ".tool-code {" in css
    assert "font-family: var(--font-mono)" in css
    assert "background: var(--code-bg)" in css
    assert "white-space: pre-wrap" in css
