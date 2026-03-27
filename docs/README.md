# janito

**janito** is a powerful CLI tool that brings AI assistants directly to your terminal. Built with function calling capabilities and MCP (Model Context Protocol) support, janito lets you interact with OpenAI-compatible AI models while accessing real-world tools and integrations.

## What is janito?

janito transforms your terminal into an AI-powered workspace. Instead of switching between browser tabs or separate applications, you can chat with AI models, manage files, check emails, and execute commands — all from a single command-line interface.

## Key Features

- **Function Calling** — Leverage built-in tools for file operations, web search, Gmail, OneDrive, and more
- **MCP Support** — Connect to Model Context Protocol servers to extend functionality with custom tools
- **Any OpenAI-Compatible API** — Works with OpenAI, local servers (LM Studio, Ollama), and custom endpoints
- **Real-time Progress** — Watch tool execution progress as it happens
- **Easy Setup** — Interactive configuration with `janito --config` or quick setup with `janito --set`

## Quick Start

```bash
# Install janito
pip install janito

# Configure your API settings
janito --config

# Start chatting
janito "Hello!"
```

## Built-in Tools

| Category | Capabilities |
|----------|--------------|
| **Files** | List, read, write, search files and directories |
| **Gmail** | Read, count, delete, move, and search emails |
| **OneDrive** | Browse, upload, download, and search files |
| **System** | Execute Python code and PowerShell commands |

## Documentation

| Section | Description |
|---------|-------------|
| [Getting Started](docs/getting-started/) | Installation and quick start guides |
| [Configuration](docs/configuration/) | Environment variables, providers, and secrets |
| [Usage](docs/usage/) | Interactive mode, logging, and single prompt mode |
| [Tools](docs/tools/) | Detailed documentation for each built-in tool |
| [Development](docs/development/) | Contributing guide |
| [Reference](docs/reference/) | CLI options and exit codes |

## License

MIT License
