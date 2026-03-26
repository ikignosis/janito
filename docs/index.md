# Janito4

**Janito4** is an OpenAI CLI (Command-Line Interface) with function calling capabilities and MCP (Model Context Protocol) support. It allows you to interact with AI models from the terminal with built-in tools and integrations.

## Features

- 🔧 **Function Calling** - Built-in tools for file operations, web search, and more
- 📧 **Gmail Integration** - Read, search, and manage emails
- ☁️ **OneDrive Integration** - Browse, upload, download, and share files
- 🔌 **MCP Support** - Connect to Model Context Protocol servers
- 📊 **Real-time Progress** - Watch tool execution progress as it happens
- 🚀 **Easy Setup** - Interactive configuration with `--config` or quick setup with `--set` flags
- 🌐 **Any OpenAI-Compatible API** - Works with OpenAI, local servers (LM Studio, Ollama), and custom endpoints

## Quick Example

```bash
# Install
pip install janito4

# Configure interactively
janito4 --config

# Start chatting
janito4 "Hello!"
```

## Why Janito4?

### Work Directly in Your Terminal

No need to switch between browser tabs or other applications. Chat with AI models while keeping your terminal workflow intact.

### Powerful Built-in Tools

Janito4 comes with tools for common tasks:

| Category | Tools |
|----------|-------|
| **Files** | List, read, write, search files and directories |
| **Gmail** | Read, count, delete, move, and search emails |
| **OneDrive** | Browse, upload, download, search files |
| **System** | Run Python code, execute PowerShell commands |

### Extend with MCP

Connect to [Model Context Protocol](https://modelcontextprotocol.io/) servers to add custom tools and capabilities.

### Works with Any Provider

Use OpenAI, local LLM servers (LM Studio, Ollama), or any OpenAI-compatible API.

## Getting Started

1. [Install Janito4](getting-started/installation.md)
2. [Configure your settings](getting-started/quick-start.md)
3. [Start chatting](usage/interactive-mode.md)

## License

MIT License
