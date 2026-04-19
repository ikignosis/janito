# Using janito with Environment Variables

This guide explains how to configure janito using environment variables.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | Base URL of the OpenAI-compatible API | `https://api.openai.com` |
| `OPENAI_API_KEY` | API key for authentication | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `OPENAI_MODEL` | Model name/deployment name to use | `gpt-4`, `gpt-3.5-turbo`, `your-local-model` |

## Usage

### Unix/Linux/macOS

```bash
# For standard OpenAI API
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"

# For OpenAI-compatible endpoints
export OPENAI_BASE_URL="https://api.openai.com"          # For OpenAI (explicit)
# export OPENAI_BASE_URL="http://localhost:8080/v1"     # For local servers like LM Studio, Ollama, etc.
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_MODEL="gpt-4"                              # Or your preferred model

# Use the CLI
python -m janito "Your prompt here"
```

### Windows (PowerShell)

```powershell
# For standard OpenAI API
$env:OPENAI_API_KEY = "sk-your-openai-key"
$env:OPENAI_MODEL = "gpt-4"

# For OpenAI-compatible endpoints
$env:OPENAI_BASE_URL = "https://api.openai.com"
# $env:OPENAI_BASE_URL = "http://localhost:8080/v1"    # For local servers
$env:OPENAI_API_KEY = "your-api-key-here"
$env:OPENAI_MODEL = "gpt-4"

# Use the CLI
python -m janito "Your prompt here"
```

## Examples

### OpenAI API

```bash
export OPENAI_BASE_URL="https://api.openai.com"
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"
python -m janito "Explain quantum computing in simple terms"
```

### Local LLM (e.g., LM Studio, Ollama)

```bash
export OPENAI_BASE_URL="http://localhost:1234/v1"  # LM Studio default
export OPENAI_API_KEY="not-needed"                 # Often not required for local servers
export OPENAI_MODEL="local-model-name"
python -m janito "What is 2+2?"
```

### Custom Provider (e.g., MiniMax)

Configure the provider using CLI, then set credentials via environment variables:

```bash
# Configure provider (writes to config.json)
janito --set provider=custom --set endpoint="https://api.minimax.chat/minimax/v1" --set model="MiniMax-M2.7"

# Set API key via environment variable
export OPENAI_API_KEY="your-minimax-api-key"
python -m janito "Hello"
```

## Notes

- Environment variables take precedence over saved configuration
- For security, avoid hardcoding API keys in scripts; consider using a `.env` file with a tool like `python-dotenv`
- CLI options (`--set`, `--set-api-key`, `--config`) override environment variables at runtime
  - Note: `--set` and `--set-api-key` must be used in **separate commands**
