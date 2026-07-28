#!/usr/bin/env python3
"""
Web Search Tool - A class-based tool for searching the web via the Brave
Search API.

This tool queries the Brave independent web index
(``https://api.search.brave.com/res/v1/web/search``) and returns a clean,
JSON-serialisable subset of the response (web results plus any news hits)
suitable for feeding back to the model.

The API key is read from the janito secrets store under the ``brave_api_key``
key. The tool is only loaded when that secret is present (see
``should_load``), so it is never advertised to the model unless it is
configured.

Setup:
    janito --set-secret brave_api_key=YOUR_BRAVE_SUBSCRIPTION_TOKEN

For direct execution, use: python -m janito.tools.net.web_search [args]
For AI function calling, use through the tool registry (tooling.tools_registry).
"""

import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ...tooling import BaseTool
from ..decorator import tool

# Brave Search API base URL and web-search path.
_BRAVE_BASE_URL = "https://api.search.brave.com/res"
_SEARCH_PATH = "/v1/web/search"

# Secret key under which the Brave subscription token is stored.
_BRAVE_SECRET_KEY = "brave_api_key"  # pragma: allowlist secret

# Valid values for the ``safesearch`` parameter.
_VALID_SAFESEARCH = ("off", "moderate", "strict")

# Maximum number of web results the API will return per request.
_MAX_COUNT = 20

# Default request timeout (seconds).
_REQUEST_TIMEOUT = 15

# Snippets longer than this are truncated to keep the model context small.
_MAX_SNIPPET_LEN = 500


def _resolve_api_key() -> str | None:
    """Resolve the Brave Search subscription token from the secrets store."""
    try:
        from ...secrets_config import get_secret

        return get_secret(_BRAVE_SECRET_KEY)
    except Exception:
        return None


def _clean_text(text: str | None) -> str:
    """Strip HTML decoration markers and unescape entities to plain text.

    Brave returns snippets with highlighting tags (``<strong>``) and HTML
    entities (``&quot;``, ``&#x27;``, ``&amp;`` …). The model only needs the
    plain text, so tags are removed and entities unescaped.
    """
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)  # drop any HTML tags
    text = html.unescape(text)  # &quot; -> ", &#x27; -> ', &amp; -> &
    return " ".join(text.split())  # collapse whitespace


def _truncate(text: str | None, limit: int = _MAX_SNIPPET_LEN) -> str:
    """Clean a snippet and trim it to ``limit`` characters (ellipsis if cut)."""
    text = _clean_text(text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _extract_web_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull a clean list of web results out of a Brave Search response."""
    results: list[dict[str, Any]] = []
    web = data.get("web") or {}
    for item in web.get("results", []) or []:
        results.append(
            {
                "title": _clean_text(item.get("title")),
                "url": item.get("url", ""),
                "description": _truncate(item.get("description")),
                "age": item.get("age", ""),
                "language": item.get("language", ""),
            }
        )
    return results


def _extract_news_results(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull a clean list of news results out of a Brave Search response."""
    results: list[dict[str, Any]] = []
    news = data.get("news") or {}
    for item in news.get("results", []) or []:
        results.append(
            {
                "title": _clean_text(item.get("title")),
                "url": item.get("url", ""),
                "description": _truncate(item.get("description")),
                "source": item.get("source", ""),
                "age": item.get("age", ""),
            }
        )
    return results


@tool(permissions="r")
class WebSearch(BaseTool):
    """
    Tool for searching the web using the Brave Search API.

    Returns a ranked list of web pages (and any news hits) relevant to the
    query, drawn from Brave's independent search index. Use this when you need
    up-to-date information from the web.

    Requires the ``brave_api_key`` secret to be configured:
        janito --set-secret brave_api_key=YOUR_BRAVE_SUBSCRIPTION_TOKEN

    Args:
        query (str): The search query (max 400 characters / 50 words). Required.
        count (int): Number of web results to return, 1-20 (default: 10).
        country (str): 2-letter country code for result origin (e.g. "US").
        search_lang (str): Language code for results (e.g. "en").
        safesearch (str): Adult-content filter: "off", "moderate", or "strict".
        freshness (str): Filter by page age: "pd" (24h), "pw" (7d), "pm" (31d),
            "py" (365d), or a custom "YYYY-MM-DDtoYYYY-MM-DD" range.
    """

    @classmethod
    def should_load(cls) -> bool:
        """Only load when the ``brave_api_key`` secret is configured."""
        if not _resolve_api_key():
            cls._load_skip_reason = (
                f"Secret '{_BRAVE_SECRET_KEY}' is not set. Configure it with: "
                f"janito --set-secret {_BRAVE_SECRET_KEY}=YOUR_BRAVE_SUBSCRIPTION_TOKEN"
            )
            return False
        return True

    def run(
        self,
        query: str,
        count: int = 10,
        country: str | None = None,
        search_lang: str | None = None,
        safesearch: str | None = None,
        freshness: str | None = None,
    ) -> dict[str, Any]:
        """
        Search the web via the Brave Search API.

        Args:
            query (str): The search query (max 400 characters / 50 words).
            count (int): Number of web results to return, 1-20 (default: 10).
            country (Optional[str]): 2-letter country code for result origin.
            search_lang (Optional[str]): Language code for results.
            safesearch (Optional[str]): "off", "moderate", or "strict".
            freshness (Optional[str]): Page-age filter ("pd"/"pw"/"pm"/"py" or
                a custom "YYYY-MM-DDtoYYYY-MM-DD" range).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'success': bool indicating if the search succeeded
                - 'query': the original query
                - 'altered_query': spellchecker-modified query (if any)
                - 'result_count': number of web results returned
                - 'results': list of {title, url, description, age, language}
                - 'news': list of {title, url, description, source, age}
                - 'execution_time_ms': request duration in milliseconds
                - 'error': error message (only present if success is False)
        """
        try:
            if not query or not query.strip():
                self.report_error("A non-empty 'query' is required")
                return {"success": False, "error": "A non-empty 'query' is required"}

            query = query.strip()

            # Validate / clamp count.
            try:
                count = int(count)
            except (TypeError, ValueError):
                count = 10
            count = max(1, min(count, _MAX_COUNT))

            if safesearch is not None and safesearch not in _VALID_SAFESEARCH:
                msg = (
                    f"Invalid safesearch {safesearch!r}; must be one of "
                    f"{', '.join(_VALID_SAFESEARCH)}"
                )
                self.report_error(msg)
                return {"success": False, "error": msg, "query": query}

            api_key = _resolve_api_key()
            if not api_key:
                msg = (
                    f"No Brave API key found. Set it with: "
                    f"janito --set-secret {_BRAVE_SECRET_KEY}=YOUR_BRAVE_SUBSCRIPTION_TOKEN"
                )
                self.report_error(msg)
                return {"success": False, "error": msg, "query": query}

            self.report_start(f"🔎 Searching the web for: {query}", end="")

            # Build query parameters (only include the ones that were set).
            params: dict[str, Any] = {"q": query, "count": count}
            if country:
                params["country"] = country
            if search_lang:
                params["search_lang"] = search_lang
            if safesearch:
                params["safesearch"] = safesearch
            if freshness:
                params["freshness"] = freshness

            url = f"{_BRAVE_BASE_URL}{_SEARCH_PATH}?{urllib.parse.urlencode(params)}"

            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")
            req.add_header("Accept-Encoding", "identity")
            req.add_header("X-Subscription-Token", api_key)
            req.add_header("User-Agent", "Mozilla/5.0 (compatible; janito/1.0)")

            start_time = time.time()
            try:
                with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    err_body = e.read().decode("utf-8", errors="replace")
                    err_data = json.loads(err_body)
                    detail = (err_data.get("error") or {}).get("detail", "")
                except Exception:
                    pass
                msg = f"HTTP Error {e.code}: {e.reason}"
                if detail:
                    msg += f" — {detail[:300]}"
                self.report_error(msg)
                return {
                    "success": False,
                    "error": msg,
                    "query": query,
                    "status_code": e.code,
                }
            except urllib.error.URLError as e:
                self.report_error(f"URL Error: {e.reason}")
                return {
                    "success": False,
                    "error": f"URL Error: {e.reason}",
                    "query": query,
                }

            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                self.report_error(f"Invalid JSON response: {e}")
                return {
                    "success": False,
                    "error": f"Invalid JSON response: {e}",
                    "query": query,
                }

            query_info = data.get("query") or {}
            results = _extract_web_results(data)
            news = _extract_news_results(data)

            execution_time_ms = int((time.time() - start_time) * 1000)
            self.report_result(
                f"{len(results)} web results"
                + (f", {len(news)} news" if news else "")
                + f" ({execution_time_ms}ms)"
            )

            return {
                "success": True,
                "query": query,
                "altered_query": query_info.get("altered"),
                "result_count": len(results),
                "results": results,
                "news": news,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            self.report_error(f"Execution error: {e!s}")
            return {
                "success": False,
                "error": f"Search failed: {e!s}",
                "query": query,
            }


# ── CLI testing harness ──────────────────────────────────────────────────
def main():
    """Command line interface for testing the WebSearch tool."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Search the web via the Brave Search API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "python asyncio tutorial"
  %(prog)s "latest AI news" --count 5 --freshness pw
  %(prog)s "best cafes" --country US --json
        """,
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=10,
        help="Number of results (1-20, default: 10)",
    )
    parser.add_argument("--country", help="2-letter country code (e.g. US)")
    parser.add_argument("--search-lang", help="Language code (e.g. en)")
    parser.add_argument(
        "--safesearch", choices=_VALID_SAFESEARCH, help="Adult-content filter"
    )
    parser.add_argument(
        "--freshness",
        help='Page-age filter: "pd", "pw", "pm", "py", or "YYYY-MM-DDtoYYYY-MM-DD"',
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    args = parser.parse_args()

    result = WebSearch().run(
        query=args.query,
        count=args.count,
        country=args.country,
        search_lang=args.search_lang,
        safesearch=args.safesearch,
        freshness=args.freshness,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✅ {result['result_count']} results for: {result['query']}")
            if result.get("altered_query"):
                print(f"   (spellchecked: {result['altered_query']})")
            for i, r in enumerate(result["results"], 1):
                print(f"\n  {i}. {r['title']}")
                print(f"     {r['url']}")
                if r["description"]:
                    print(f"     {r['description']}")
            if result.get("news"):
                print("\n  News:")
                for r in result["news"]:
                    print(f"   - {r['title']} ({r.get('source', '')}) {r['url']}")
        else:
            print(f"❌ Error: {result['error']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
