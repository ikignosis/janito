# Tools & Plugins

Janito provides a rich set of tools and plugins to extend its functionality beyond basic LLM interactions.

## Built-in Tools

All tools are available by default and can be used in chat mode with the `!tool_name` syntax.

### File Management

| Tool | Description |
|------|-------------|
| `read` | Read content from a file |
| `write` | Write content to a file |
| `copy-file` | Copy a file to a new location |
| `move-file` | Move a file to a new location |
| `remove-file` | Delete a file |
| `create-directory` | Create a new directory |
| `remove-directory` | Delete a directory |
| `find-files` | Find files matching a pattern |
| `validate-file-syntax` | Validate syntax of a file (Python, JSON, YAML, etc.) |

### Web & Network

| Tool | Description |
|------|-------------|
| `fetch-url` | Fetch content from a URL |
| `open-url` | Open a URL in the default browser |
| `open-html-in-browser` | Open an HTML file in the default browser |

### System & Development

| Tool | Description |
|------|-------------|
| `run-bash-command` | Execute a bash command |
| `run-powershell-command` | Execute a PowerShell command |
| `python-code-run` | Execute Python code snippet |
| `python-command-run` | Execute a Python command |
| `python-file-run` | Execute a Python script file |
| `view-file` | View content of a file with line numbers |
| `replace-text-in-file` | Replace text in a file |
| `search-text` | Search for text in files |
| `get-file-outline` | Get structure outline of a file |
| `search-outline` | Search within file outlines |

### Visualization

| Tool | Description |
|------|-------------|
| `show-image` | Display an image inline in the terminal |
| `show-image-grid` | Display multiple images in a grid |
| `read-chart` | Display charts and data visualizations |

### Interaction

| Tool | Description |
|------|-------------|
| `ask-user` | Prompt the user for input during execution |

## Plugin System

Janito's functionality is organized into plugins that can be enabled or disabled:

### Core Plugins

- **filemanager**: Provides file management tools
- **system**: Provides system execution tools
- **web**: Provides web interaction tools
- **codeanalyzer**: Provides code analysis tools
- **imagedisplay**: Provides image display tools
- **visualization**: Provides charting tools
- **pythondev**: Provides Python development tools

### Enabling/Disabling Plugins

```bash
# List all plugins
janito list-plugins

# Enable a plugin
janito enable-plugin webtools

# Disable a plugin
janito disable-plugin filemanager
```

> **Note**: Some tools may be disabled by default for security reasons. Use `janito list-tools` to see which tools are currently available.

## Security & Permissions

By default, tools have restricted permissions for safety:

- File operations are limited to the current working directory
- Network access is restricted to whitelisted domains
- Bash/PowerShell commands require explicit user confirmation

You can modify these restrictions using:

```bash
# Allow unrestricted file access
janito unrestricted --files

# Allow unrestricted network access
janito unrestricted --network

# Allow unrestricted command execution
janito unrestricted --commands
```

Use `janito privileges` to view your current permission levels.

> **Warning**: Disabling security restrictions reduces safety. Only do this in trusted environments.