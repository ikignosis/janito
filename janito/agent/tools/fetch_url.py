import requests
from typing import Optional
from bs4 import BeautifulSoup
from janito.agent.tool_registry import register_tool

from janito.agent.tools.tool_base import ToolBase

@register_tool(name="fetch_url")
class FetchUrlTool(ToolBase):
    """Fetch the content of a web page and extract its text."""
    def call(self, url: str, search_strings: list[str] = None) -> str:
        self.report_info(f"🌐 Fetching URL: {url} ... ")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        self.update_progress({'event': 'progress', 'message': f"Fetched URL with status {response.status_code}"})
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator='\n')

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
                text = '\n...\n'.join(filtered)
            else:
                text = "No matches found for the provided search strings."

        self.report_success("✅ Result")
        return text

