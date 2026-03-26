# Quick Start

This guide gets you up and running with Janito4 in minutes.

## 1. Configure Your Settings

The first time you run Janito4, you'll need to configure your API settings. You can do this interactively or with command-line flags.

### Interactive Configuration

Run the configuration wizard:

```bash
janito4 --config
```

You'll be prompted for:

| Setting | Description | Example |
|---------|-------------|---------|
| **Provider** | Your API provider | `openai`, `anthropic`, `azure`, `custom` |
| **API Key** | Your API key (masked for security) | `sk-xxxxxxxxxxxxxxxx` |
| **Model** | Model name to use | `gpt-4`, `claude-3-opus` |
| **Context Window** | Maximum tokens (default: 65536) | `65536` |

### Quick Configuration with Flags

Set options directly from the command line:

```bash
# OpenAI example
janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4

# Local LLM example
janito4 --set provider=openai --set model="local-model" --set-api-key="not-needed"
```

## 2. Run Your First Prompt

### Single Prompt

```bash
janito4 "What is the capital of France?"
```

### Interactive Chat

```bash
janito4
```

Type your messages and press Enter. Commands:

| Command | Description |
|---------|-------------|
| `exit` / `quit` | End the session |
| `restart` | Clear conversation history |
| `Ctrl+D` / `Ctrl+Z` | Exit the shell |

### Pipe Input

```bash
echo "Tell me a joke" | janito4
```

## 3. View Your Configuration

```bash
janito4 --show-config
```

## Examples

### OpenAI

```bash
janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4 "Explain quantum computing"
```

### Local LLM (LM Studio, Ollama)

```bash
janito4 --set provider=openai --set model="local-model" --set-api-key="not-needed" "What is 2+2?"
```

### Azure OpenAI

```bash
janito4 --set provider=azure --set-api-key="your-key" --set model="gpt-4" "Hello"
```

### Custom Provider

```bash
janito4 --set provider=custom --set endpoint="http://localhost:8000/v1" --set model="my-model" "Hello"
```

## What's Next?

- Learn about [interactive chat mode](../usage/interactive-mode.md)
- Explore [built-in tools](../tools/index.md)
- Set up [Gmail integration](../tools/gmail.md) or [OneDrive](../tools/onedrive.md)
- Connect to [MCP servers](../tools/mcp.md)
