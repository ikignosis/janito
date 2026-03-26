# Tools

Janito4 includes built-in tools for common tasks.

## Available Tools

| Category | Tools | Description |
|----------|-------|-------------|
| **Files** | File operations | List, read, write, search files and directories |
| **Gmail** | Email management | Read, count, delete, move, and search emails |
| **OneDrive** | Cloud storage | Browse, upload, download, search files |
| **System** | Execution | Run Python code, execute PowerShell commands |
| **Skills** | Extensions | Install and use task-specific skills |
| **MCP** | Extensions | Connect to MCP servers for custom tools |

## Enabling Tools

Tools are automatically available in chat mode. For single prompts:

```bash
# File tools are always available
janito4 "Read the README.md file"

# Enable Gmail tools
janito4 --gmail "Show my unread emails"

# Enable OneDrive tools
janito4 --onedrive "List my files"
```

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
- [Gmail Tools](gmail.md)
- [OneDrive Tools](onedrive.md)
- [Skills](skills.md)
- [MCP Support](mcp.md)
