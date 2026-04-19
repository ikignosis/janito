# Quick Start

This guide gets you up and running with janito in minutes.

## 1. Configure Your Settings

The first time you run janito, you'll need to configure your API settings. You can do this interactively or with command-line flags.

### Interactive Configuration

Run the configuration wizard:

```bash
janito --config
```

You'll be prompted for:

| Setting | Description | Example |
|---------|-------------|---------|
| **Provider** | Your API provider | `openai`, `custom` |
| **API Key** | Your API key (masked for security) | `sk-xxxxxxxxxxxxxxxx` |
| **Model** | Model name to use | `gpt-4`, `claude-3-opus` |
| **Context Window** | Maximum tokens (default: 65536) | `65536` |

### Quick Configuration with Flags

Set options directly from the command line. Note that `--set` and `--set-api-key` must be used in **separate commands**:

```bash
# OpenAI example (two steps: config, then API key)
janito --set provider=openai --set model=gpt-4
janito --set-api-key="sk-your-key" --provider openai

# Local LLM example
janito --set provider=openai --set model="local-model"
janito --set-api-key="not-needed" --provider openai
```

## 2. Run Your First Prompt

### Single Prompt

```bash
janito "What is the capital of France?"
```

### Interactive Chat

```bash
janito
```

Type your messages and press Enter. Commands:

| Command | Description |
|---------|-------------|
| `exit` / `quit` | End the session |
| `restart` | Clear conversation history |
| `Ctrl+D` / `Ctrl+Z` | Exit the shell |

### Pipe Input

```bash
echo "Tell me a joke" | janito
```

## 3. View Your Configuration

```bash
janito --show-config
```

## Examples

### OpenAI

```bash
# Step 1: Set provider and model
janito --set provider=openai --set model=gpt-4
# Step 2: Store API key
janito --set-api-key="sk-your-key" --provider openai
# Step 3: Run prompt
janito "Explain quantum computing"
```

### Local LLM (LM Studio, Ollama)

```bash
# Step 1: Set provider and model
janito --set provider=openai --set model="local-model"
# Step 2: Store placeholder API key
janito --set-api-key="not-needed" --provider openai
# Step 3: Run prompt
janito "What is 2+2?"
```

### Custom Provider

```bash
# Step 1: Set provider, endpoint, and model
janito --set provider=custom --set endpoint="http://localhost:8000/v1" --set model="my-model"
# Step 2: Run prompt
janito "Hello"
```

## What's Next?

- Learn about [interactive chat mode](../usage/interactive-mode.md)
- Explore [built-in tools](../tools/index.md)
- Set up [Gmail integration](../tools/gmail.md) or [OneDrive](../tools/onedrive.md)
- Connect to [MCP servers](../tools/mcp.md)
