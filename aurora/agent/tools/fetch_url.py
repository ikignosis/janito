import requests
from bs4 import BeautifulSoup
from aurora.agent.tool_handler import ToolHandler
from aurora.agent.tools.rich_utils import print_info, print_success, print_error

@ToolHandler.register_tool
def fetch_url(url: str, search_strings: list[str] = None) -> str:
    """
    Fetch the content of a web page and extract its text.

    url: The URL to fetch.
    search_strings: Optional list of strings to filter the extracted text around those strings.
    """
    print_info(f"🌐 Fetching URL: {url} ... ")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

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

        print_success("✅ Success")
        return text
    except Exception as e:
        print_error(f"❌ Error: {e}")
        return f"❌ Failed to fetch URL '{url}': {e}"
