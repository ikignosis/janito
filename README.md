# Janito4 - an OpenAI CLI with function calling and MCP

## Features

- 🔧 **Function Calling** - Built-in tools for file operations, web search, and more
- 📧 **Gmail Integration** - Read, search, and manage emails
- ☁️ **OneDrive Integration** - Browse, upload, download, and share files
- 🔌 **MCP Support** - Connect to Model Context Protocol servers
- 📊 **Real-time Progress** - Watch tool execution progress as it happens
- 🚀 **Easy Setup** - Interactive configuration with `--config` or quick setup with `--set` flags
- 🔗 **Any OpenAI-Compatible API** - Works with OpenAI, local servers (LM Studio, Ollama), and custom endpoints

## Quick Start

```bash
# Install
pip install janito4

# Configure interactively
janito4 --config

# Or set options directly
janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4

# Start chatting
janito4 "Hello!"
```

## Installation

### From PyPI

```bash
pip install janito4
```

For development setup, see [README_DEV.md](README_DEV.md).

## Configuration

### Interactive Setup

```bash
janito4 --config
```

You'll be prompted for:
- **Provider** - `openai`, `anthropic`, `azure`, or `custom`
- **API Key** - Masked for security
- **Model** - e.g., `gpt-4`, `gpt-3.5-turbo`
- **Context Window** - Max tokens (default: 65536)

### Quick Configuration with `--set`

Set options directly from the command line:

```bash
# Set the provider
janito4 --set provider=openai

# Set your API key
janito4 --set-api-key="sk-your-key-here"

# Set the model
janito4 --set model=gpt-4

# Combine multiple options
janito4 --set provider=openai --set model=gpt-4 --set-api-key="sk-your-key"
```

### View Configuration

```bash
janito4 --show-config
```

### Available Options

| Option | Description | Example |
|--------|-------------|---------|
| `provider` | Provider name | `openai`, `anthropic`, `azure`, `custom` |
| `model` | Model name | `gpt-4`, `claude-3-opus` |
| `context-window` | Context window size | `65536` |

For custom endpoints (base-url), see [README_LOCAL.md](README_LOCAL.md).

## Usage

### Single Prompt

```bash
janito4 "What is the capital of France?"
```

### Pipe Input

```bash
echo "Tell me a joke" | janito4
```

### Interactive Chat

```bash
janito4
```

Commands in chat mode:
- `exit` / `quit` - End session
- `restart` - Clear conversation history
- `Ctrl+D` / `Ctrl+Z` - Exit

### Logging

```bash
janito4 --log=info "Your prompt"      # Info level
janito4 --log=debug "Your prompt"     # Debug level
janito4 --log=info,debug "Your prompt" # Multiple levels
```

## Examples

### OpenAI

```bash
janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4 "Explain quantum computing"
```

### Local LLM (LM Studio, Ollama)

```bash
janito4 --set provider=openai --set-api-key="not-needed" --set model="local-model" "What is 2+2?"
```

### Azure OpenAI

```bash
janito4 --set provider=azure --set-api-key="your-key" --set model="gpt-4" "Hello"
```

## Built-in Tools

Janito4 includes tools for common tasks:

### Email Integration (Gmail)

```bash
# Authenticate with Gmail
janito4 --gmail-auth

# Use Gmail in chat mode
janito4 --gmail

# Check emails
janito4 --gmail "Show my unread emails from today"
```

For full Gmail documentation, see [janito4/tools/README.gmail.md](janito4/tools/README.gmail.md).

### Cloud Storage (OneDrive)

```bash
# Authenticate with Microsoft OneDrive
janito4 --onedrive-auth

# Use OneDrive in chat mode
janito4 --onedrive

# List files
janito4 --onedrive "List my files in Documents"
```

For full OneDrive documentation, see [janito4/tools/README.onedrive.md](janito4/tools/README.onedrive.md).

### File Operations

```bash
# List files
janito4.tools.files.list_files . --recursive --pattern "*.py"

# Read file
janito4.tools.files.read_file README.md --max-lines 20
```

### Web Search

```bash
janito4 "Search the web for the latest Python news"
```

### MCP Tools

Connect to MCP servers using the `/mcp` command inside the interactive shell:

```bash
# Add a stdio-based MCP server
/mcp add myserver stdio python -m mcp.server

# Add an HTTP-based MCP server
/mcp add remote http https://api.example.com/mcp

# List configured servers
/mcp list
```

For full MCP documentation, see [README_MCP.md](README_MCP.md).

## Tool Progress Reporting

Tools report progress in real-time:

```
🔄 Reading files...
📊 Processing: 50/100 files
✅ Completed: 100 files (2.3MB)
```

Progress messages go to stderr so they don't interfere with tool output.

## Error Handling

| Exit Code | Meaning |
|-----------|---------|
| `0` | Success |
| `1` | Configuration or runtime error |
| `130` | User cancelled (Ctrl+C) |

## Dependencies

- Python 3.6+
- `openai>=1.0.0`
- `rich>=10.0.0`
- `prompt-toolkit>=3.0.0`
- `requests` (for MCP support)

## License

MIT License
