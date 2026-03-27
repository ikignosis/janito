# Using janito with Custom Providers (Local/MiniMax)

This guide explains how to use janito with custom OpenAI-compatible API endpoints, such as local servers or third-party providers like MiniMax.

## Quick Start

### Command Line Arguments

You can pass configuration directly via command-line arguments:

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:8000/minimax/v1 \
  --set model=MiniMax-M2.7 \
  --set-api-key=your-api-key-here \
  "Your prompt here"
```

### Interactive Configuration

First, configure your settings interactively:

```bash
python -m janito --config
```

When prompted, select or enter:
- **Provider**: `custom`
- **Endpoint URL**: `http://localhost:8000/minimax/v1`
- **Model name**: `MiniMax-M2.7`
- **API key**: Your API key (if required by your endpoint)
- **Context window size**: Press Enter for default (65536) or specify a value

After configuration, you can use janito without specifying the endpoint each time:

```bash
python -m janito "Your prompt here"
```

## Command-Line Arguments Reference

| Argument | Description | Example |
|----------|-------------|---------|
| `--set provider=xxx` | Provider type (openai, azure, custom) | `custom` |
| `--set endpoint=xxx` | Full API endpoint URL | `http://localhost:8000/minimax/v1` |
| `--set model=xxx` | Model name to use | `MiniMax-M2.7` |
| `--set-api-key=xxx` | API key for authentication (optional if not required) | `sk-xxxxx` |

## Usage Examples

### Single Prompt

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:8000/minimax/v1 \
  --set model=MiniMax-M2.7 \
  "What is 2+2?"
```

### Interactive Chat Mode

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:8000/minimax/v1 \
  --set model=MiniMax-M2.7
```

This starts an interactive session. Type your messages and press Enter. Type `exit` or `quit` to end.

### Pipe Input

```bash
echo "Explain quantum computing" | python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:8000/minimax/v1 \
  --set model=MiniMax-M2.7
```

### With Tools

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:8000/minimax/v1 \
  --set model=MiniMax-M2.7 \
  "Read the first 10 lines of README.md and summarize it"
```

### Enable Logging

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:8000/minimax/v1 \
  --set model=MiniMax-M2.7 \
  --log=debug \
  "Hello"
```

## Common Use Cases

### Local LM Studio / Ollama Server

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=http://localhost:1234/v1 \
  --set model=local-model-name \
  --set-api-key=not-needed \
  "Your question"
```

### MiniMax API

```bash
python -m janito \
  --set provider=custom \
  --set endpoint=https://api.minimax.chat/minimax/v1 \
  --set model=MiniMax-M2.7 \
  --set-api-key=your-minimax-api-key \
  "Your question"
```

### Azure OpenAI

```bash
python -m janito \
  --set provider=azure \
  --set endpoint=https://your-resource.openai.azure.com \
  --set model=your-deployment-name \
  --set-api-key=your-azure-key \
  "Your question"
```

## Troubleshooting

### Connection Errors

- **Check if the server is running**: Ensure your local server (e.g., `localhost:8000`) is running
- **Verify the endpoint URL**: Make sure the URL matches exactly (including `/v1` suffix)
- **Check firewall settings**: Ensure the port is accessible

### Authentication Errors

- **Invalid API key**: Verify your API key is correct
- **Missing API key**: Some local servers don't require an API key - try setting `--set-api-key=not-needed`

### Model Not Found

- **Check model name**: Ensure the model name matches exactly what your endpoint expects
- **List available models**: Check your server's documentation for available models

### Getting Help

```bash
# Show all available options
python -m janito --help
```

## Tips

1. **Save configuration**: Use `--config` once to save your settings, then use the CLI without arguments
2. **Combine with tools**: The custom provider works with all janito tools (file operations, web search, etc.)
3. **Use aliases**: Add a shell alias for quick access:

   ```bash
   # ~/.bashrc or ~/.zshrc
   alias janito-local='python -m janito --set provider=custom --set endpoint=http://localhost:8000/minimax/v1 --set model=MiniMax-M2.7'
   ```

   Then simply run: `janito-local "Your question"`
