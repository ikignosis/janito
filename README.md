# janito - an OpenAI CLI with function calling and MCP

> 📖 **Full documentation available at [https://ikignosis.org/janito/](https://ikignosis.org/janito/)**

## Features

- 🔧 **Function Calling** - Built-in tools for file operations, web search, and more
- 📧 **Gmail Integration** - Read, search, and manage emails
- ☁️ **OneDrive Integration** - Browse, upload, download, and share files
- 🔌 **MCP Support** - Connect to Model Context Protocol servers
- 🧩 **Skills** - Install and use task-specific skills from GitHub
- 📊 **Real-time Progress** - Watch tool execution progress as it happens
- 🚀 **Easy Setup** - Interactive configuration with `--config` or quick setup with `--set` flags
- 🔗 **Any OpenAI-Compatible API** - Works with OpenAI, local servers (LM Studio, Ollama), and custom endpoints

## Quick Start

```bash
# Install
pip install janito

# Configure interactively
janito --config

# Or set options directly (two steps: config, then API key)
janito --set provider=openai --set model=gpt-4
janito --set-api-key="sk-your-key" --provider openai

# Start chatting
janito "Hello!"
```

## Installation

### From PyPI

```bash
pip install janito
```

For development setup, see [README_DEV.md](README_DEV.md).

## Configuration

### Interactive Setup

```bash
janito --config
```

You'll be prompted for:
- **Provider** - `openai` or `custom`
- **API Key** - Masked for security
- **Model** - e.g., `gpt-4`, `gpt-3.5-turbo`
- **Context Window** - Max tokens (default: 65536)

### Quick Configuration with `--set`

Set options directly from the command line:

```bash
# Single key-value
janito --set model=gpt-4
```

You can also use `--get`, `--unset`, and `--set-secret` with multiple values.

### View Configuration

```bash
janito --show-config
```

### Available Options

| Option | Description | Example |
|--------|-------------|---------|
| `provider` | Provider name | `openai`, `custom` |
| `model` | Model name | `gpt-4`, `claude-3-opus` |
| `context-window` | Context window size | `65536` |

For custom endpoints (base-url), see [README_LOCAL.md](README_LOCAL.md).

## Usage

### Single Prompt

```bash
janito "What is the capital of France?"
```

### Pipe Input

```bash
echo "Tell me a joke" | janito
```

### Interactive Chat

```bash
janito
```

Commands in chat mode:
- `exit` / `quit` - End session
- `restart` - Clear conversation history
- `Ctrl+D` / `Ctrl+Z` - Exit

### Logging

```bash
janito --log=info "Your prompt"      # Info level
janito --log=debug "Your prompt"     # Debug level
janito --log=info,debug "Your prompt" # Multiple levels
```

## Examples

### OpenAI

```bash
# Step 1: Set provider and model
janito --set provider=openai --set model=gpt-4
# Step 2: Store API key
janito --set-api-key="sk-your-key" --provider openai

# Then run any prompt
janito "Explain quantum computing"
```

### Alibaba (Qwen)

```bash
# Step 1: Set provider and model
janito --set provider=alibaba --set model=qwen-plus
# Step 2: Store API key
janito --set-api-key="your-dashscope-api-key" --provider alibaba

# Then run any prompt
janito "Explain quantum computing"
```

### Custom Endpoint

```bash
janito --set provider=custom --set base-url=http://localhost:8000/v1
```

## Built-in Tools

janito includes tools for common tasks:

### Email Integration (Gmail)

```bash
# Use Gmail in chat mode
janito --gmail

# Check emails
janito --gmail "Show my unread emails from today"
```

For full Gmail documentation, see [README.gmail.md](README.gmail.md).

### Cloud Storage (OneDrive)

```bash
# Authenticate with Microsoft OneDrive
janito --onedrive-auth

# Use OneDrive in chat mode
janito --onedrive

# List files
janito --onedrive "List my files in Documents"
```

For full OneDrive documentation, see [README.onedrive.md](README.onedrive.md).

### File Operations

```bash
# List files
janito.tools.files.list_files . --recursive --pattern "*.py"

# Read file
janito.tools.files.read_file README.md --max-lines 20
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
