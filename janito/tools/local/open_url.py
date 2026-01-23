import webbrowser

from janito.tooling.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tooling.loop_protection_decorator import protect_against_loops



class OpenUrlTool(ToolBase):
    permissions = ToolPermissions(read=True)

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="url")
    def run(self, url: str) -> str:
        """
        Open the supplied URL or local file in the default web browser.

        Args:
            url (str): The URL or local file path (as a file:// URL) to open. Supports both web URLs (http, https) and local files (file://).
        Returns:
            str: Status message indicating the result.
        """
        if not url.strip():
            self.report_warning(tr("ℹ️ Empty URL provided."))
            return tr("Warning: Empty URL provided. Operation skipped.")
        self.report_action(tr("🌐 Opening URL '{url}' ...", url=url), ReportAction.READ)
        try:
            webbrowser.open(url)
        except Exception as err:
            self.report_error(
                tr("❗ Error opening URL: {url}: {err}", url=url, err=str(err))
            )
            return tr("Warning: Error opening URL: {url}: {err}", url=url, err=str(err))
        self.report_success(tr("✅ URL opened in browser: {url}", url=url))
        return tr("URL opened in browser: {url}", url=url)
