import requests
import time
import os
import json
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.i18n import tr
from janito.tools.tool_utils import pluralize
from janito.tools.loop_protection_decorator import protect_against_loops


@register_local_tool
class FetchUrlTool(ToolBase):
    """
    Fetch the content of a web page and extract its text.

    This tool implements a **session-based caching mechanism** that provides
    **in-memory caching** for the lifetime of the tool instance. URLs are cached
    in RAM during the session, providing instant access to previously fetched
    content without making additional HTTP requests.

    **Session Cache Behavior:**
    - **Lifetime**: Cache exists for the lifetime of the FetchUrlTool instance
    - **Scope**: In-memory (RAM) cache, not persisted to disk
    - **Storage**: Successful responses are cached as raw HTML content
    - **Key**: Cache key is the exact URL string
    - **Invalidation**: Cache is automatically cleared when the tool instance is destroyed
    - **Performance**: Subsequent requests for the same URL return instantly

    **Error Cache Behavior:**
    - HTTP 403 errors: Cached for 24 hours (more permanent)
    - HTTP 404 errors: Cached for 1 hour (temporary)
    - Other 4xx errors: Cached for 30 minutes
    - 5xx errors: Not cached (retried on each request)

    Args:
        url (str): The URL of the web page to fetch.
        search_strings (list[str], optional): Strings to search for in the page content.
        max_length (int, optional): Maximum number of characters to return. Defaults to 5000.
        max_lines (int, optional): Maximum number of lines to return. Defaults to 200.
        context_chars (int, optional): Characters of context around search matches. Defaults to 400.
        timeout (int, optional): Timeout in seconds for the HTTP request. Defaults to 10.
        save_to_file (str, optional): File path to save the full resource content. If provided,
            the complete response will be saved to this file instead of being processed.
        headers (Dict[str, str], optional): Custom HTTP headers to send with the request.
        cookies (Dict[str, str], optional): Custom cookies to send with the request.
        follow_redirects (bool, optional): Whether to follow HTTP redirects. Defaults to True.
    Returns:
        str: Extracted text content from the web page, or a warning message. Example:
            - "<main text content...>"
            - "No lines found for the provided search strings."
            - "Warning: Empty URL provided. Operation skipped."
    """

    permissions = ToolPermissions(read=True)
    tool_name = "fetch_url"

    def __init__(self):
        super().__init__()
        self.cache_dir = Path.home() / ".janito" / "cache" / "fetch_url"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "error_cache.json"
        self.session_cache = (
            {}
        )  # In-memory session cache - lifetime matches tool instance
        self._load_cache()

        # Browser-like session with cookies and headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        # Load cookies from disk if they exist
        self.cookies_file = self.cache_dir / "cookies.json"
        self._load_cookies()

    def _load_cache(self):
        """Load error cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.error_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.error_cache = {}
        else:
            self.error_cache = {}

    def _save_cache(self):
        """Save error cache to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.error_cache, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write cache

    def _load_cookies(self):
        """Load cookies from disk into session."""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    cookies_data = json.load(f)
                    for cookie in cookies_data:
                        self.session.cookies.set(**cookie)
            except (json.JSONDecodeError, IOError):
                pass  # Silently fail if we can't load cookies

    def _save_cookies(self):
        """Save session cookies to disk."""
        try:
            cookies_data = []
            for cookie in self.session.cookies:
                cookies_data.append(
                    {
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain,
                        "path": cookie.path,
                    }
                )
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies_data, f, indent=2)
        except IOError:
            pass  # Silently fail if we can't write cookies

    def _get_cached_error(self, url: str) -> tuple[str, bool]:
        """
        Check if we have a cached error for this URL.
        Returns (error_message, is_cached) tuple.
        """
        if url not in self.error_cache:
            return None, False

        entry = self.error_cache[url]
        current_time = time.time()

        # Different expiration times for different status codes
        if entry["status_code"] == 403:
            # Cache 403 errors for 24 hours (more permanent)
            expiration_time = 24 * 3600
        elif entry["status_code"] == 404:
            # Cache 404 errors for 1 hour (more temporary)
            expiration_time = 3600
        else:
            # Cache other 4xx errors for 30 minutes
            expiration_time = 1800

        if current_time - entry["timestamp"] > expiration_time:
            # Cache expired, remove it
            del self.error_cache[url]
            self._save_cache()
            return None, False

        return entry["message"], True

    def _cache_error(self, url: str, status_code: int, message: str):
        """Cache an HTTP error response."""
        self.error_cache[url] = {
            "status_code": status_code,
            "message": message,
            "timestamp": time.time(),
        }
        self._save_cache()

    def _fetch_url_content(
        self,
        url: str,
        timeout: int = 10,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        follow_redirects: bool = True,
    ) -> str:
        """Fetch URL content and handle HTTP errors.

        Implements two-tier caching:
        1. Session cache: In-memory cache for successful responses (lifetime = tool instance)
        2. Error cache: Persistent disk cache for HTTP errors with different expiration times

        Also implements URL whitelist checking and browser-like behavior.
        """
        # Check URL whitelist
        from janito.tools.url_whitelist import get_url_whitelist_manager

        whitelist_manager = get_url_whitelist_manager()

        if not whitelist_manager.is_url_allowed(url):
            error_message = tr("Blocked")
            self.report_error(
                tr("❗ Blocked"),
                ReportAction.READ,
            )
            return error_message

        # Check session cache first
        if url in self.session_cache:
            return self.session_cache[url]

        # Check persistent cache for known errors
        cached_error, is_cached = self._get_cached_error(url)
        if cached_error:
            self.report_warning(
                tr(
                    "ℹ️ Using cached HTTP error for URL: {url}",
                    url=url,
                ),
                ReportAction.READ,
            )
            return cached_error

        try:
            # Merge custom headers with default ones
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)

            # Merge custom cookies
            if cookies:
                self.session.cookies.update(cookies)

            response = self.session.get(
                url,
                timeout=timeout,
                headers=request_headers,
                allow_redirects=follow_redirects,
            )
            response.raise_for_status()
            content = response.text

            # Save cookies after successful request
            self._save_cookies()

            # Cache successful responses in session cache
            self.session_cache[url] = content
            return content
        except requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response else None

            # Map status codes to descriptions
            status_descriptions = {
                400: "Bad Request",
                401: "Unauthorized",
                403: "Forbidden",
                404: "Not Found",
                405: "Method Not Allowed",
                408: "Request Timeout",
                409: "Conflict",
                410: "Gone",
                413: "Payload Too Large",
                414: "URI Too Long",
                415: "Unsupported Media Type",
                429: "Too Many Requests",
                500: "Internal Server Error",
                501: "Not Implemented",
                502: "Bad Gateway",
                503: "Service Unavailable",
                504: "Gateway Timeout",
                505: "HTTP Version Not Supported",
            }

            if status_code and 400 <= status_code < 500:
                description = status_descriptions.get(status_code, "Client Error")
                error_message = f"HTTP {status_code} {description}"
                # Cache 403 and 404 errors
                if status_code in [403, 404]:
                    self._cache_error(url, status_code, error_message)

                self.report_error(
                    f"❗ HTTP {status_code} {description}",
                    ReportAction.READ,
                )
                return error_message
            else:
                status_code_str = str(status_code) if status_code else "Error"
                description = status_descriptions.get(
                    status_code,
                    (
                        "Server Error"
                        if status_code and status_code >= 500
                        else "Client Error"
                    ),
                )
                self.report_error(
                    f"❗ HTTP {status_code_str} {description}",
                    ReportAction.READ,
                )
                return f"HTTP {status_code_str} {description}"
        except requests.exceptions.ConnectionError as conn_err:
            self.report_error(
                "❗ Network Error",
                ReportAction.READ,
            )
            return f"Network Error: Failed to connect to {url}"
        except requests.exceptions.Timeout as timeout_err:
            self.report_error(
                "❗ Timeout Error",
                ReportAction.READ,
            )
            return f"Timeout Error: Request timed out after {timeout} seconds"
        except requests.exceptions.RequestException as req_err:
            self.report_error(
                "❗ Request Error",
                ReportAction.READ,
            )
            return f"Request Error: {str(req_err)}"
        except Exception as err:
            self.report_error(
                "❗ Error fetching URL",
                ReportAction.READ,
            )
            return f"Error: {str(err)}"

    def _extract_and_clean_text(self, html_content: str) -> str:
        """Extract and clean text from HTML content."""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n")

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _filter_by_search_strings(
        self, text: str, search_strings: list[str], context_chars: int
    ) -> str:
        """Filter text by search strings with context."""
        filtered = []
        for s in search_strings:
            idx = text.find(s)
            if idx != -1:
                start = max(0, idx - context_chars)
                end = min(len(text), idx + len(s) + context_chars)
                snippet = text[start:end]
                filtered.append(snippet)

        if filtered:
            return "\n...\n".join(filtered)
        else:
            return tr("No lines found for the provided search strings.")

    def _apply_limits(self, text: str, max_length: int, max_lines: int) -> str:
        """Apply length and line limits to text."""
        # Apply length limit
        if len(text) > max_length:
            text = text[:max_length] + "\n... (content truncated due to length limit)"

        # Apply line limit
        lines = text.splitlines()
        if len(lines) > max_lines:
            text = (
                "\n".join(lines[:max_lines])
                + "\n... (content truncated due to line limit)"
            )

        return text

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="url")
    def run(
        self,
        url: str,
        search_strings: list[str] = None,
        max_length: int = 5000,
        max_lines: int = 200,
        context_chars: int = 400,
        timeout: int = 10,
        save_to_file: str = None,
        headers: Dict[str, str] = None,
        cookies: Dict[str, str] = None,
        follow_redirects: bool = True,
    ) -> str:
        if not url.strip():
            self.report_warning(tr("ℹ️ Empty URL provided."), ReportAction.READ)
            return tr("Warning: Empty URL provided. Operation skipped.")

        self.report_action(tr("🌐 Fetch URL '{url}' ...", url=url), ReportAction.READ)

        # Check if we should save to file
        if save_to_file:
            html_content = self._fetch_url_content(
                url,
                timeout=timeout,
                headers=headers,
                cookies=cookies,
                follow_redirects=follow_redirects,
            )
            if (
                html_content.startswith("HTTP Error ")
                or html_content == "Error"
                or html_content == "Blocked"
            ):
                return html_content

            try:
                with open(save_to_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                file_size = len(html_content)
                self.report_success(
                    tr(
                        "✅ Saved {size} bytes to {file}",
                        size=file_size,
                        file=save_to_file,
                    ),
                    ReportAction.READ,
                )
                return tr("Successfully saved content to: {file}", file=save_to_file)
            except IOError as e:
                error_msg = tr("Error saving to file: {error}", error=str(e))
                self.report_error(error_msg, ReportAction.READ)
                return error_msg

        # Normal processing path
        html_content = self._fetch_url_content(
            url,
            timeout=timeout,
            headers=headers,
            cookies=cookies,
            follow_redirects=follow_redirects,
        )
        if (
            html_content.startswith("HTTP Error ")
            or html_content == "Error"
            or html_content == "Blocked"
        ):
            return html_content

        # Extract and clean text
        text = self._extract_and_clean_text(html_content)

        # Filter by search strings if provided
        if search_strings:
            text = self._filter_by_search_strings(text, search_strings, context_chars)

        # Apply limits
        text = self._apply_limits(text, max_length, max_lines)

        # Report success
        num_lines = len(text.splitlines())
        total_chars = len(text)
        self.report_success(
            tr(
                "✅ {num_lines} {line_word}, {chars} chars",
                num_lines=num_lines,
                line_word=pluralize("line", num_lines),
                chars=total_chars,
            ),
            ReportAction.READ,
        )
        return text
