# Tools Index

Janito provides a comprehensive set of tools for file operations, code execution, web access, and more. Tools can be selectively disabled using the [disabled tools configuration](guides/disabled-tools.md).

## Available Tools

### Visualization Tools

#### show_image

Display an image inline in the terminal using rich.

Arguments:
- path (str): Path to the image file.
- width (int, optional): Target width in terminal cells. If unset, auto-fit.
- height (int, optional): Target height in terminal rows. If unset, auto-fit.
- preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

Returns:
- Status message indicating display result or error details.

Example Usage:
- show a PNG: `show_image(path="img/tux.png", width=60)`

#### show_image_grid

Display multiple images in a grid inline in the terminal using rich.

Arguments:
- paths (list[str]): List of image file paths.
- columns (int, optional): Number of columns in the grid. Default: 2.
- width (int, optional): Max width for each image cell. Default: None (auto).
- height (int, optional): Max height for each image cell. Default: None (auto).
- preserve_aspect (bool, optional): Preserve aspect ratio. Default: True.

Returns:
- Status string summarizing the grid display.

Example Usage:
- `show_image_grid(paths=["img/tux.png", "img/tux_display.png"], columns=2, width=40)`

#### read_chart

Display charts and data visualizations in the terminal using rich.

**Arguments:**

- `data` (dict): Chart data in JSON format. Should contain 'type' (bar, line, pie, table) and 'data' keys.
- `title` (str, optional): Chart title. Defaults to "Chart".
- `width` (int, optional): Chart width. Defaults to 80.
- `height` (int, optional): Chart height. Defaults to 20.

**Returns:**

- Formatted chart display in terminal or error message.

**Example Usage:**

- Display a table: `read_chart(data={"type": "table", "data": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}, title="Users")`
- Display a bar chart: `read_chart(data={"type": "bar", "data": {"Q1": 100, "Q2": 150}}, title="Sales")`
- Display a pie chart: `read_chart(data={"type": "pie", "data": {"Desktop": 45, "Mobile": 30}}, title="Usage")`

### Web Tools

#### open_url

Opens the supplied URL or local file in the default web browser.

**Arguments:**

- `url` (str): The URL or local file path (as a file:// URL) to open. Supports both web URLs (http, https) and local files (file://).

**Returns:**

- Status message indicating the result.

**Example Usage:**

- Open a website: `open_url(url="https://example.com")`
- Open a local file: `open_url(url="file:///C:/path/to/file.html")`

This tool replaces the previous `open_html_in_browser` tool, and can be used for both web and local files.

### search_text

Search for a text query in files or directories.

**Arguments:**

- `paths` (str): Space-separated list of file or directory paths to search in.
- `query` (str): Text or regular expression to search for.
- `use_regex` (bool): Treat `query` as a regex pattern (default: False).
- `case_sensitive` (bool): Enable case-sensitive search (default: False).
- `max_depth` (int): Maximum directory depth to search (default: 0 = unlimited).
- `max_results` (int): Maximum matching lines to return (default: 100).
- `count_only` (bool): Return only match counts instead of lines (default: False).

**Returns:**

- Matching lines with file paths and line numbers, or match counts if `count_only=True`.

**Example Usage:**

- Plain-text search: `search_text(paths="src", query="TODO")`
- Regex search: `search_text(paths="src tests", query=r"def\s+\w+", use_regex=True)`
- Case-insensitive count: `search_text(paths="docs", query="janito", case_sensitive=False, count_only=True)`

## Tool Management

### Disabling Tools

You can disable specific tools using configuration:

```bash
# Disable interactive prompts
janito --set disabled_tools=ask_user

# Disable code execution
janito --set disabled_tools=python_code_run,run_powershell_command

# View current disabled tools and config file path
janito --show-config
```

### Listing Available Tools

See all currently available tools:

```bash
janito --list-tools
```

For complete documentation on tool disabling, see the [Disabling Tools Guide](guides/disabled-tools.md).
