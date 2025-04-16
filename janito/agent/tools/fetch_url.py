import requests
from typing import Optional, Callable
from bs4 import BeautifulSoup
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error

@ToolHandler.register_tool
def fetch_url(url: str, search_strings: list[str] = None, on_progress: Optional[Callable[[dict], None]] = None) -> str:
    """
    Fetch the content of a web page and extract its text.

    Args:
        url (str): The URL to fetch.
        search_strings (list[str], optional): List of strings to filter the extracted text around those strings.
        on_progress (callable, optional): Callback function for streaming progress updates.
    """
    print_info(f"\U0001F310 Fetching URL: {url} ... ")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    if on_progress:
        on_progress({'event': 'fetched', 'status_code': response.status_code})
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

    print_success("\u2705 Success")
    return text
