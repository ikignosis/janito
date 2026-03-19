# Janito4 - OpenAI CLI

A simple command-line interface to interact with OpenAI-compatible endpoints (including OpenAI, Azure OpenAI, or any OpenAI-compatible API) with built-in function calling capabilities.

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

Set the following environment variables:

```bash
# For standard OpenAI API (OPENAI_BASE_URL is optional)
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"

# For OpenAI-compatible endpoints (set OPENAI_BASE_URL)
export OPENAI_BASE_URL="https://api.openai.com"          # For OpenAI (explicit)
# export OPENAI_BASE_URL="https://your-azure-endpoint.openai.azure.com"  # For Azure OpenAI
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

### Azure OpenAI:
```bash
export OPENAI_BASE_URL="https://your-resource.openai.azure.com"
export OPENAI_API_KEY="your-azure-api-key"
export OPENAI_MODEL="your-deployment-name"
python -m janito4 "Summarize this text: ..."
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

## Tool Permissions System

Tools must declare their required permissions using the `@tool` decorator with the `permissions` parameter. This allows the system to understand what capabilities each tool requires and enables permission-based security controls.

### Permission Types

- **`r`**: Read access (files, directories, system information)
- **`w`**: Write access (create, modify, delete files/directories)  
- **`x`**: Execute access (run commands, scripts, programs)
- **`n`**: Network access (HTTP requests, network operations)

Permissions can be combined (e.g., `"rw"`, `"rwx"`).

### Usage Example

```python
from janito4.tooling import BaseTool
from janito4.tools.decorator import tool

@tool(permissions="r")
class ReadFileTool(BaseTool):
    """Tool for reading files from the filesystem."""
    
    def run(self, filepath: str):
        """Read a file from the filesystem."""
        self.report_start(f"Reading file: {filepath}")
        # Implementation here
        return {"success": True, "content": "file content"}

@tool(permissions="rw")  
class WriteFileTool(BaseTool):
    """Tool for writing content to files."""
    
    def run(self, filepath: str, content: str):
        """Write content to a file."""
        self.report_start(f"Writing to file: {filepath}")
        # Implementation here  
        return {"success": True, "message": "File written successfully"}
```

### Accessing Permissions

The permissions system provides functions to query tool permissions:

```python
from janito4.tooling.tools_registry import get_tool_permissions, get_all_tool_permissions

# Get permissions for a specific tool
perms = get_tool_permissions("read_file")  # Returns "r"

# Get all tool permissions
all_perms = get_all_tool_permissions()  # Returns {"read_file": "r", "write_file": "rw", ...}
```

## Tool Progress Reporting

Tools can report their progress in real-time using the built-in progress reporting system located in `tooling/progress/`. This provides transparency into what the AI agent is doing during tool execution.

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

## Error Handling

The CLI will exit with appropriate error codes:

- `1`: Configuration or runtime errors
- `130`: User cancelled operation (Ctrl+C)

## Dependencies

- Python 3.6+
- `requests` library

## License

MIT License