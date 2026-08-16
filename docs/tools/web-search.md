# Web Tools

janito provides tools for accessing the web: fetching content from URLs, searching
the web, and rendering pages with a headless browser.

All tools live in the dedicated **`net`** toolset (`janito/tools/net/`), which is
auto-loaded, so they are available in every session without extra flags. `WebSearch`
additionally gates itself on the `brave_api_key` secret (see [Setup](#setup)) and is
only advertised to the model once that secret is configured. `HeadlessBrowse`
gates itself on the presence of a Google Chrome (or Chromium-based) browser binary.

## Setup

### WebSearch (Brave Search)

The `WebSearch` tool searches the web via the [Brave Search API](https://brave.com/search/api/)
(`GET /res/v1/web/search`), querying Brave's independent search index. It is only loaded
when the `brave_api_key` secret is set.

1. Create an account and get a subscription token from the [Brave Search API](https://brave.com/search/api/)
2. Store the token as a janito secret:

```bash
# Set your Brave Search subscription token
janito --set-secret brave_api_key=your-brave-subscription-token
```

That's it — `WebSearch` is now available. You can verify the secret is stored with:

```bash
janito --list-secrets        # shows secret names (never values)
janito --get-secret brave_api_key
```

See [Secrets](../configuration/secrets.md) for more on the secrets store.

### GetUrl

`GetUrl` fetches content from any `http://` or `https://` URL and requires no setup.

### HeadlessBrowse

`HeadlessBrowse` renders a URL with **headless Google Chrome** and returns the
page's DOM. Unlike `GetUrl` (a plain HTTP fetch), it executes JavaScript, so it sees
content that only appears after the page's scripts run (SPAs, client-side rendering,
etc.). It requires **no setup** — but it is only loaded when a Google Chrome (or
Chromium-based) binary is found on the system. If Chrome is missing, the tool is
simply not advertised to the model (check `/tools` for the skip reason).

## Available Tools

| Tool | Description | Permissions |
|------|-------------|-------------|
| `GetUrl` | Fetch content from a URL | `r` |
| `WebSearch` | Search the web via the Brave Search API | `r` |
| `HeadlessBrowse` | Render a URL with headless Chrome (runs JavaScript) | `r` |

## Usage

### Example Prompts

```bash
# Search the web (requires the brave_api_key secret)
janito "Search the web for the latest Python release notes"

# Search and then read a result
janito "Find recent news about AI agents and summarize the top result"

# Fetch a URL directly
janito "Fetch https://example.com and summarize it"

# Render a JavaScript-heavy page with headless Chrome
janito "Browse https://example.com with headless Chrome and summarize what it shows"
```

### GetUrl Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | — | The URL to fetch (must be `http://` or `https://`). Required. |
| `max_length` | int | `5000` | Maximum number of characters to return |
| `max_lines` | int | `200` | Maximum number of lines to return |
| `timeout` | int | `10` | Request timeout in seconds |
| `follow_redirects` | bool | `True` | Whether to follow HTTP redirects |
| `threshold` | int | `10000` | Content size (chars) above which the full content is written to a temporary file instead of being returned inline |

When fetched content exceeds `threshold`, it is stored in a temporary file (removed on
exit) and the tool returns the file path plus a message to explore it with search tools,
instead of blowing up the model context.

### HeadlessBrowse Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | — | The URL to browse (must be `http://` or `https://`). Required. |
| `max_length` | int | `10000` | Maximum number of characters to return |
| `max_lines` | int | `500` | Maximum number of lines to return |
| `timeout` | int | `30` | Chrome process timeout in seconds |
| `wait_ms` | int | `1000` | Virtual time budget (ms) to let JavaScript run before dumping the DOM |
| `threshold` | int | `10000` | DOM size (chars) above which the full content is written to a temporary file instead of being returned inline |

The `wait_ms` parameter controls how long the page's JavaScript is allowed to run —
increase it for heavily scripted pages. As with `GetUrl`, oversized DOMs are stored in
a temporary file (removed on exit) rather than returned inline.

### WebSearch Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | — | The search query (max 400 characters / 50 words). Required. |
| `count` | int | `10` | Number of web results to return, 1–20 |
| `country` | str | — | 2-letter country code for result origin (e.g. `"US"`) |
| `search_lang` | str | — | Language code for results (e.g. `"en"`) |
| `safesearch` | str | — | Adult-content filter: `"off"`, `"moderate"`, or `"strict"` |
| `freshness` | str | — | Page-age filter: `"pd"` (24h), `"pw"` (7d), `"pm"` (31d), `"py"` (365d), or a custom `"YYYY-MM-DDtoYYYY-MM-DD"` range |

The response is a clean, model-friendly list of web results (`title`, `url`, truncated
`description`, `age`, `language`) plus any `news` hits, along with the result count and
the request duration.

## Troubleshooting

### "Secret 'brave_api_key' is not set"

`WebSearch` is not loaded because the secret is missing. Run:

```bash
janito --set-secret brave_api_key=your-brave-subscription-token
```

### "HTTP Error 401" / "HTTP Error 403"

The subscription token is invalid or rejected by Brave. Re-check the token at
[brave.com/search/api](https://brave.com/search/api/) and set it again with
`janito --set-secret brave_api_key=...`.

### "URL must start with http:// or https://"

`GetUrl` only supports HTTP and HTTPS URLs.

### "Google Chrome (or another Chromium-based browser) was not found"

`HeadlessBrowse` is not loaded because no Chrome/Chromium binary was found on
the system. Install [Google Chrome](https://www.google.com/chrome/) (or Chromium,
Brave, or Microsoft Edge) and restart janito. The tool finds the browser via `PATH`
plus the standard macOS and Windows install locations.

## More Info

- Source: [`janito/tools/net/`](https://github.com/joaompinto/janito/tree/main/janito/tools/net)
- [Secrets](../configuration/secrets.md) - Full secrets setup guide
