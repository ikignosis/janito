# Janito4 - OpenAI CLI

A powerful command-line interface for interacting with OpenAI-compatible APIs. Features built-in function calling, MCP support, real-time tool progress reporting, and an extensible tool system.

## Features

- 🚀 **Easy Setup** - Interactive configuration with `--config` or quick setup with `--set` flags
- 🔧 **Function Calling** - Built-in tools for file operations, web search, and more
- 📊 **Real-time Progress** - Watch tool execution progress as it happens
- 🔌 **Any OpenAI-Compatible API** - Works with OpenAI, Azure, local servers (LM Studio, Ollama), and custom endpoints
- 💬 **Multiple Modes** - Single prompts, piped input, or interactive chat sessions
- 🛠️ **Extensible** - Easy to add custom tools with automatic schema generation

## Quick Start

```bash
# Install
pip install janito4

# Configure interactively
python -m janito4 --config

# Or set options directly
python -m janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4

# Start chatting
python -m janito4 "Hello!"
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
python -m janito4 --config
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
python -m janito4 --set provider=openai

# Set your API key
python -m janito4 --set-api-key="sk-your-key-here"

# Set the model
python -m janito4 --set model=gpt-4

# Combine multiple options
python -m janito4 --set provider=openai --set model=gpt-4 --set-api-key="sk-your-key"
```

### View Configuration

```bash
python -m janito4 --show-config
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
python -m janito4 "What is the capital of France?"
```

### Pipe Input

```bash
echo "Tell me a joke" | python -m janito4
```

### Interactive Chat

```bash
python -m janito4
```

Commands in chat mode:
- `exit` / `quit` - End session
- `restart` - Clear conversation history
- `Ctrl+D` / `Ctrl+Z` - Exit

### Logging

```bash
python -m janito4 --log=info "Your prompt"      # Info level
python -m janito4 --log=debug "Your prompt"     # Debug level
python -m janito4 --log=info,debug "Your prompt" # Multiple levels
```

## Examples

### OpenAI

```bash
python -m janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4 "Explain quantum computing"
```

### Local LLM (LM Studio, Ollama)

```bash
python -m janito4 --set provider=openai --set-api-key="not-needed" --set model="local-model" "What is 2+2?"
```

### Azure OpenAI

```bash
python -m janito4 --set provider=azure --set-api-key="your-key" --set model="gpt-4" "Hello"
```

## Built-in Tools

Janito4 includes tools for common tasks:

### File Operations

```bash
# List files
python -m janito4.tools.files.list_files . --recursive --pattern "*.py"

# Read file
python -m janito4.tools.files.read_file README.md --max-lines 20
```

### Web Search

```bash
python -m janito4 "Search the web for the latest Python news"
```

### MCP Tools

Connect to MCP servers for additional tools:

```bash
python -m janito4 --mcp-server=myserver "Use the read_file tool"
```

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
