import requests
from typing import Optional
from bs4 import BeautifulSoup
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error
from janito.agent.tools.tool_base import ToolBase

class FetchUrlTool(ToolBase):
    """Fetch the content of a web page and extract its text."""
    def call(self, url: str, search_strings: list[str] = None) -> str:
        print_info(f"🌐 Fetching URL: {url} ... ", end="")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        self.update_progress(f"Fetched URL with status {response.status_code}")
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

        print_success("✅ Result")
        return text

ToolHandler.register_tool(FetchUrlTool, name="fetch_url")
