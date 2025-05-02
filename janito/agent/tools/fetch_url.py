import requests
from bs4 import BeautifulSoup
from janito.agent.tool_registry import register_tool
from janito.agent.tool_base import ToolBase
from janito.i18n import tr
from janito.agent.tools_utils.utils import pluralize


@register_tool(name="fetch_url")
class FetchUrlTool(ToolBase):
    """
    Fetch the content of a web page and extract its text.
    Args:
        url (str): The URL of the web page to fetch.
        search_strings (list[str], optional): Strings to search for in the page content.
    Returns:
        str: Extracted text content from the web page, or a warning message. Example:
            - "<main text content...>"
            - "No lines found for the provided search strings."
            - "Warning: Empty URL provided. Operation skipped."
    """

    def run(self, url: str, search_strings: list[str] = None) -> str:
        if not url.strip():
            self.report_warning(tr("ℹ️ Empty URL provided."))
            return tr("Warning: Empty URL provided. Operation skipped.")
        self.report_info(tr("🌐 Fetching URL '{url}' ...", url=url))
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        self.update_progress(
            {
                "event": "progress",
                "message": tr(
                    "Fetched URL with status {status}", status=response.status_code
                ),
            }
        )
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        if search_strings:
            filtered = []
            for s in search_strings:
                idx = text.find(s)
                if idx != -1:
                    start = max(0, idx - 200)
                    end = min(len(text), idx + len(s) + 200)
                    snippet = text[start:end]
                    filtered.append(snippet)
            if filtered:
                text = "\n...\n".join(filtered)
            else:
                text = tr("No lines found for the provided search strings.")
        num_lines = len(text.splitlines())
        self.report_success(
            tr(
                "✅ {num_lines} {line_word}",
                num_lines=num_lines,
                line_word=pluralize("line", num_lines),
            )
        )
        return text
