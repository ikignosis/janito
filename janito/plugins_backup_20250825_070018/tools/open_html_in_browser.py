import os
import webbrowser
from janito.plugins.tools.decorators import register_core_tool
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tools.loop_protection_decorator import protect_against_loops


@register_core_tool
class OpenHtmlInBrowser(ToolBase):
    """
    Open the supplied HTML file in the default web browser.

    Args:
        path (str): Path to the HTML file to open.
    Returns:
        str: Status message indicating the result.
    """

    permissions = ToolPermissions(read=True)
    tool_name = "open_html_in_browser"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(self, path: str) -> str:
        if not path.strip():
            self.report_warning(tr("ℹ️ Empty file path provided."))
            return tr("Warning: Empty file path provided. Operation skipped.")
        if not os.path.isfile(path):
            self.report_error(tr("❗ File does not exist: {path}", path=path))
            return tr("Warning: File does not exist: {path}", path=path)
        if not path.lower().endswith((".html", ".htm")):
            self.report_warning(tr("⚠️ Not an HTML file: {path}", path=path))
            return tr("Warning: Not an HTML file: {path}", path=path)
        url = "file://" + os.path.abspath(path)
        self.report_action(
            tr("📖 Opening HTML file in browser: {path}", path=path), ReportAction.READ
        )
        try:
            webbrowser.open(url)
        except Exception as err:
            self.report_error(
                tr("❗ Error opening HTML file: {path}: {err}", path=path, err=str(err))
            )
            return tr(
                "Warning: Error opening HTML file: {path}: {err}",
                path=path,
                err=str(err),
            )
        self.report_success(tr("✅ HTML file opened in browser: {path}", path=path))
        return tr("HTML file opened in browser: {path}", path=path)
