"""Contract tests for the web tools info dialog.

The session-start banner's "N tool(s) active" text is a link that opens a
modal dialog showing the same tools listing the ``/tools`` command renders
(built-in tools with permission badges, skipped tools, MCP tools and a
summary footer). The data is fetched by the same ``_fetchToolsListing()``
helper the ``/tools`` command uses, so the dialog never drifts from the
command output.

These tests pin down the frontend wiring:

1. ``chatCommands.js`` exposes ``openToolsDialog`` / ``closeToolsDialog`` and
   reuses ``_fetchToolsListing`` for the dialog payload;
2. ``chat.js`` initialises the dialog state;
3. ``index.html`` renders the banner link bound to ``openToolsDialog`` and the
   modal template (``toolsDialogOpen``) with the tools sections;
4. ``tools.css`` styles the link affordance and the dialog card.
"""

from pathlib import Path

from _frontend import render_index_html

FRONTEND = Path(__file__).parent.parent.parent / "janito" / "web" / "frontend"


def test_chat_commands_expose_dialog_handlers():
    """openToolsDialog/closeToolsDialog live in the chatCommands mixin."""
    js = (FRONTEND / "js" / "chatCommands.js").read_text(encoding="utf-8")
    assert "async openToolsDialog() {" in js
    assert "closeToolsDialog() {" in js
    # The dialog payload comes from the same fetcher as /tools.
    assert "this.toolsDialog = await _fetchToolsListing();" in js
    # Lazy load: nothing is refetched once the listing is cached.
    assert "if (this.toolsDialog) return;" in js


def test_chat_component_initialises_dialog_state():
    """chat.js declares the reactive dialog state."""
    js = (FRONTEND / "js" / "chat.js").read_text(encoding="utf-8")
    assert "toolsDialogOpen: false," in js
    assert "toolsDialog: null," in js
    assert "toolsDialogLoading: false," in js
    assert "toolsDialogError: null," in js


def test_index_html_banner_link_opens_dialog():
    """The active-tools count in the session-start banner is a link."""
    html = render_index_html()
    assert 'class="ssb-tools-link"' in html
    assert '@click.prevent="openToolsDialog()"' in html
    # The link wraps the count, not the whole banner.
    banner_start = html.index('class="session-start-banner"')
    link_pos = html.index('class="ssb-tools-link"', banner_start)
    assert html.index('x-text="toolsSummary.active"', banner_start) > link_pos
    # The skipped count is NOT part of the link (it follows the separator).
    assert html.index('x-text="toolsSummary.skipped"', banner_start) > link_pos


def test_index_html_renders_dialog_template():
    """The tools dialog modal reuses the /tools panel classes."""
    html = render_index_html()
    assert 'x-if="toolsDialogOpen"' in html
    assert 'class="modal-card tools-dialog"' in html
    assert 'class="tools-dialog-body"' in html
    assert '@click.self="closeToolsDialog()"' in html
    # The three /tools sections are present inside the dialog.
    assert "Built-in Tools" in html
    assert "Skipped Tools" in html
    assert "MCP Tools" in html
    assert "tools-panel-footer" in html
    # Permission badges render exactly like the /tools panel.
    assert "permLabel(t.permissions)" in html


def test_tools_css_styles_link_and_dialog():
    """tools.css gives the banner link and dialog their own styles."""
    css = (FRONTEND / "css" / "tools.css").read_text(encoding="utf-8")
    assert ".ssb-tools-link {" in css
    assert "cursor: pointer" in css
    assert ".tools-dialog.modal-card {" in css
    # The dialog is a bounded modal: a definite height (capped at 70vh) so it
    # never stretches to fill the viewport, with the tools list scrolling
    # inside the body rather than growing the whole card.
    assert "height: min(70vh, 640px)" in css
    assert "min-height: 260px" in css
    assert ".tools-dialog-body {" in css
    assert "overflow-y: auto" in css
