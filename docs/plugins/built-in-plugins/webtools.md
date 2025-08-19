# Web Tools Plugin

## Overview

The Web Tools plugin provides functionality for web scraping, browsing, and URL operations. This plugin enables interaction with web resources, retrieval of online content, and browser integration.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|
| `fetch_url` | Download web page content | Retrieves content from URLs with options for text extraction, search filtering, and timeout control |
| `open_url` | Open URLs in default browser | Opens web URLs in the system's default web browser |
| `open_html_in_browser` | Open local HTML files in browser | Displays local HTML files in the default web browser for preview and inspection |

## Usage Examples

### Fetching Web Content
```json
{
  "tool": "fetch_url",
  "url": "https://example.com",
  "max_length": 5000,
  "timeout": 10
}
```

### Opening a Web Page
```json
{
  "tool": "open_url",
  "url": "https://github.com/janito"
}
```

### Previewing HTML Output
```json
{
  "tool": "open_html_in_browser",
  "path": "output/report.html"
}
```

## Configuration

This plugin does not require any specific configuration. Network operations use default timeout values and respect robots.txt when possible.

## Security Considerations

- URL access is subject to the URL whitelist configuration
- Web scraping is limited to prevent excessive requests
- Local file access for HTML preview is restricted to project directories
- Sensitive domains require explicit user approval

## Integration

The Web Tools plugin integrates with the data acquisition system to provide:

- Research capabilities through web content retrieval
- Documentation generation with web-based references
- Real-time data collection from online sources
- Interactive web content preview

This enables seamless integration between local development and web-based resources while maintaining security controls.