# Using Janito4 with Custom Providers (Local/MiniMax)

This guide explains how to use Janito4 with custom OpenAI-compatible API endpoints, such as local servers or third-party providers like MiniMax.

## Quick Start

### Command Line Arguments

You can pass configuration directly via command-line arguments:

```bash
python -m janito4 \
  --provider custom \
  --endpoint http://localhost:8000/minimax/v1 \
  --model MiniMax-M2.7 \
  --api-key your-api-key-here \
  "Your prompt here"
```

### Interactive Configuration

First, configure your settings interactively:

```bash
python -m janito4 --config
```

When prompted, select or enter:
- **Provider**: `custom`
- **Endpoint URL**: `http://localhost:8000/minimax/v1`
- **Model name**: `MiniMax-M2.7`
- **API key**: Your API key (if required by your endpoint)
- **Context window size**: Press Enter for default (65536) or specify a value

After configuration, you can use Janito4 without specifying the endpoint each time:

```bash
python -m janito4 "Your prompt here"
```

## Command-Line Arguments Reference

| Argument | Description | Example |
|----------|-------------|---------|
| `--provider` | Provider type (openai, azure, custom) | `custom` |
| `--endpoint` | Full API endpoint URL | `http://localhost:8000/minimax/v1` |
| `--model` | Model name to use | `MiniMax-M2.7` |
| `--api-key` | API key for authentication (optional if not required) | `sk-xxxxx` |

## Environment Variables (Alternative)

Instead of command-line arguments, you can set environment variables:

```bash
# Unix/Linux/macOS
export JANITO_PROVIDER=custom
export OPENAI_BASE_URL=http://localhost:8000/minimax/v1
export OPENAI_MODEL=MiniMax-M2.7
export OPENAI_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:JANITO_PROVIDER = "custom"
$env:OPENAI_BASE_URL = "http://localhost:8000/minimax/v1"
$env:OPENAI_MODEL = "MiniMax-M2.7"
$env:OPENAI_API_KEY = "your-api-key-here"
```

Then simply run:

```bash
python -m janito4 "Your prompt here"
```

## Usage Examples

### Single Prompt

```bash
python -m janito4 \
  --provider custom \
  --endpoint http://localhost:8000/minimax/v1 \
  --model MiniMax-M2.7 \
  "What is 2+2?"
```

### Interactive Chat Mode

```bash
python -m janito4 \
  --provider custom \
  --endpoint http://localhost:8000/minimax/v1 \
  --model MiniMax-M2.7
```

This starts an interactive session. Type your messages and press Enter. Type `exit` or `quit` to end.

### Pipe Input

```bash
echo "Explain quantum computing" | python -m janito4 \
  --provider custom \
  --endpoint http://localhost:8000/minimax/v1 \
  --model MiniMax-M2.7
```

### With Tools

```bash
python -m janito4 \
  --provider custom \
  --endpoint http://localhost:8000/minimax/v1 \
  --model MiniMax-M2.7 \
  "Read the first 10 lines of README.md and summarize it"
```

### Enable Logging

```bash
python -m janito4 \
  --provider custom \
  --endpoint http://localhost:8000/minimax/v1 \
  --model MiniMax-M2.7 \
  --log=debug \
  "Hello"
```

## Common Use Cases

### Local LM Studio / Ollama Server

```bash
python -m janito4 \
  --provider custom \
  --endpoint http://localhost:1234/v1 \
  --model local-model-name \
  --api-key not-needed \
  "Your question"
```

### MiniMax API

```bash
python -m janito4 \
  --provider custom \
  --endpoint https://api.minimax.chat/minimax/v1 \
  --model MiniMax-M2.7 \
  --api-key your-minimax-api-key \
  "Your question"
```

### Azure OpenAI

```bash
python -m janito4 \
  --provider azure \
  --endpoint https://your-resource.openai.azure.com \
  --model your-deployment-name \
  --api-key your-azure-key \
  "Your question"
```

## Troubleshooting

### Connection Errors

- **Check if the server is running**: Ensure your local server (e.g., `localhost:8000`) is running
- **Verify the endpoint URL**: Make sure the URL matches exactly (including `/v1` suffix)
- **Check firewall settings**: Ensure the port is accessible

### Authentication Errors

- **Invalid API key**: Verify your API key is correct
- **Missing API key**: Some local servers don't require an API key - try setting `--api-key not-needed`

### Model Not Found

- **Check model name**: Ensure the model name matches exactly what your endpoint expects
- **List available models**: Check your server's documentation for available models

### Getting Help

```bash
# Show all available options
python -m janito4 --help
```

## Tips

1. **Save configuration**: Use `--config` once to save your settings, then use the CLI without arguments
2. **Combine with tools**: The custom provider works with all Janito4 tools (file operations, web search, etc.)
3. **Use aliases**: Add a shell alias for quick access:

   ```bash
   # ~/.bashrc or ~/.zshrc
   alias janito-local='python -m janito4 --provider custom --endpoint http://localhost:8000/minimax/v1 --model MiniMax-M2.7'
   ```

   Then simply run: `janito-local "Your question"`
