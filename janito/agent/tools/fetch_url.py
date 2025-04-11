import requests
from bs4 import BeautifulSoup
from janito.agent.tool_handler import ToolHandler
from janito.agent.tools.rich_utils import print_info, print_success, print_error

@ToolHandler.register_tool
def fetch_url(url: str, search_strings: list[str] = None, on_progress: callable = None) -> str:
    """
    Fetch the content of a web page and extract its text.

    url: The URL to fetch.
    search_strings: Optional list of strings to filter the extracted text around those strings.
    on_progress: Optional callback function for streaming progress updates.
    """
    if on_progress:
        on_progress({'event': 'start', 'url': url})
    print_info(f"\U0001F310 Fetching URL: {url} ... ")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        if on_progress:
            on_progress({'event': 'fetched', 'status_code': response.status_code})
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

        print_success("\u2705 Success")
        if on_progress:
            on_progress({'event': 'done'})
        return text
    except Exception as e:
        print_error(f"\u274c Error: {e}")
        if on_progress:
            on_progress({'event': 'error', 'error': str(e)})
        return f"\u274c Failed to fetch URL '{url}': {e}"
