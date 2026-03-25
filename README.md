# Janito4 - OpenAI CLI

A simple command-line interface to interact with OpenAI-compatible endpoints (including OpenAI or any OpenAI-compatible API) with built-in function calling capabilities.

## Features

- Uses environment variables for configuration (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`)
- Accepts prompts as command-line arguments or from stdin
- Works with any OpenAI-compatible endpoint
- Simple and lightweight
- **Real-time tool progress reporting** - Tools can show their progress during execution
- **Extensible tool system** - Easy to add new tools with automatic schema generation

## Installation

1. Clone this repository or download the files

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. The package can be used directly from the source directory, or installed in development mode:
   ```bash
   pip install -e .
   ```

## Configuration

### Interactive Configuration Setup

You can set up your configuration interactively using the `--config` flag:

```bash
python -m janito4 --config
```

This will prompt you for:
- **Provider name** (e.g., openai, anthropic, azure) - lists available providers
- **API key** - masked for security, shows existing key if available
- **Model name** - the model to use
- **Context window size** - max tokens (default: 65536)

Existing configuration values are used as defaults, so you can just press Enter to keep them.

### Manual Configuration

Set the following environment variables:

```bash
# For standard OpenAI API (OPENAI_BASE_URL is optional)
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"

# For OpenAI-compatible endpoints (set OPENAI_BASE_URL)
export OPENAI_BASE_URL="https://api.openai.com"          # For OpenAI (explicit)

# export OPENAI_BASE_URL="http://localhost:8080/v1"      # For local servers like LM Studio, Ollama, etc.
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_MODEL="gpt-4"                              # Or your preferred model
```

## Usage

### Single Prompt Mode (command-line argument):
```bash
python -m janito4 "What is the capital of France?"
```

### Pipe Input Mode:
```bash
echo "Tell me a joke" | python -m janito4
```

### Interactive Chat Mode:
```bash
python -m janito4
# Starts an interactive chat session where you can have multi-turn conversations
# Type 'exit' or 'quit' to end the session, 'restart' to clear conversation history, or press Ctrl+D/Ctrl+Z
```

### Logging:
```bash
# Enable info logging
python -m janito4 --log=info "Your prompt"

# Enable debug logging for detailed output
python -m janito4 --log=debug "Your prompt"

# Enable multiple log levels
python -m janito4 --log=info,debug "Your prompt"

# Enable warning and error only
python -m janito4 --log=warning,error "Your prompt"
```

## Examples

### OpenAI API:
```bash
export OPENAI_BASE_URL="https://api.openai.com"
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"
python -m janito4 "Explain quantum computing in simple terms"
```

### Local LLM (e.g., LM Studio, Ollama):
```bash
export OPENAI_BASE_URL="http://localhost:1234/v1"  # LM Studio default
export OPENAI_API_KEY="not-needed"                 # Often not required for local servers
export OPENAI_MODEL="local-model-name"
python -m janito4 "What is 2+2?"
```

### PowerShell Usage:
```powershell
# Set environment variables for current session
$env:OPENAI_BASE_URL = "https://api.openai.com"
$env:OPENAI_API_KEY = "your-api-key-here"
$env:OPENAI_MODEL = "gpt-4"

# Use the CLI
python -m janito4 "What is the capital of France?"
echo "Tell me a joke" | python -m janito4
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | Base URL of the OpenAI-compatible API | `https://api.openai.com` |
| `OPENAI_API_KEY` | API key for authentication | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `OPENAI_MODEL` | Model name/deployment name to use | `gpt-4`, `gpt-3.5-turbo`, `your-local-model` |

## Tool Progress Reporting

Tools can report their progress in real-time using the built-in progress reporting system. This provides transparency into what the AI agent is doing during tool execution.

### Direct Tool Execution

Individual tools can be executed directly using Python's module syntax:
```bash
python -m janito4.tools.files.list_files . --recursive --pattern "*.py"
python -m janito4.tools.files.read_file README.md --max-lines 10
```

Tools are now implemented as classes that inherit from `BaseTool` and must implement a `run()` method. The `@tool` decorator is applied to the class, and the system automatically creates a wrapper function for AI function calling compatibility.

This allows for testing and debugging tools independently while still having access to the full tooling infrastructure including progress reporting.

- **🔄 Start messages**: Indicate when a tool operation begins
- **📊 Progress messages**: Show ongoing work (e.g., "Processing item 50/100")
- **✅ Result messages**: Report successful completion with statistics
- **❌ Error messages**: Display errors that occur during execution
- **⚠️ Warning messages**: Show non-critical warnings

Progress messages are displayed via `stderr` so they don't interfere with the tool's actual return value that gets sent back to the AI model.

### MCP Tool Progress Reporting

MCP tools also report their progress using the same system:

```
 🔄 MCP tool: myserver_read_file [myserver]
 ✅ returned 50 lines (2048 chars)
```

When calling an MCP tool, you'll see:
1. **Start message** with the tool name
2. **Progress message** showing which service is handling the call
3. **Result message** summarizing the output (e.g., "returned 50 lines", "returned keys: success, content")

This provides the same transparency for MCP tools as built-in tools, making it easy to track what the AI agent is doing across both local and remote tool sources.

## Error Handling

The CLI will exit with appropriate error codes:

- `1`: Configuration or runtime errors
- `130`: User cancelled operation (Ctrl+C)

## Dependencies

- Python 3.6+
- `requests` library

## License

MIT License