# Tools

janito includes built-in tools for common tasks.

## Available Tools

| Category | Tools | Description |
|----------|-------|-------------|
| **Files** | File operations | List, read, write, search files and directories |
| **Code Search** | Code search | Search a pre-built trigram index (codesearch plugin, `/codesearch`) |
| **System** | Execution | Run Python code, execute PowerShell commands |
| **Net** | Web access | Fetch URLs, search the web (Brave) |
| **Skills** | Extensions | Install and use task-specific skills |
| **MCP** | Extensions | Connect to MCP servers for custom tools |

## Enabling Tools

Tools are automatically available in chat mode. For single prompts:

```bash
# File tools are always available
janito "Read the README.md file"
```

Tool integrations that are not built-in (Gmail, code search, OneDrive) are
provided by plugins — see [Plugins](PLUGINS.md).

## Tool Progress

Tools report progress in real-time:

```
📖 Reading files...
📊 Processing: 50/100 files
✅ Completed: 100 files (2.3MB)
```

Progress messages go to stderr so they don't interfere with tool output.

## Related Topics

- [File Tools](files.md)
- [Code Search](codesearch.md) - Search a pre-built trigram index (codesearch plugin)
- [Web Tools](web-search.md) - Fetch URLs and search the web (Brave)
- [Skills](skills.md)
- [MCP Support](mcp.md)
