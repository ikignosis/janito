# Using Janito4 with Environment Variables

This guide explains how to configure Janito4 using environment variables.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | Base URL of the OpenAI-compatible API | `https://api.openai.com` |
| `OPENAI_API_KEY` | API key for authentication | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `OPENAI_MODEL` | Model name/deployment name to use | `gpt-4`, `gpt-3.5-turbo`, `your-local-model` |
| `JANITO_PROVIDER` | Provider type (openai, azure, custom) | `openai`, `azure`, `custom` |

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

# For custom providers
export JANITO_PROVIDER="custom"
export OPENAI_BASE_URL="http://localhost:8000/minimax/v1"
export OPENAI_MODEL="MiniMax-M2.7"
export OPENAI_API_KEY="your-api-key-here"

# For Azure OpenAI
export JANITO_PROVIDER="azure"
export OPENAI_BASE_URL="https://your-resource.openai.azure.com"
export OPENAI_MODEL="your-deployment-name"
export OPENAI_API_KEY="your-azure-key"

# Use the CLI
python -m janito4 "Your prompt here"
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

# For custom providers
$env:JANITO_PROVIDER = "custom"
$env:OPENAI_BASE_URL = "http://localhost:8000/minimax/v1"
$env:OPENAI_MODEL = "MiniMax-M2.7"
$env:OPENAI_API_KEY = "your-api-key-here"

# For Azure OpenAI
$env:JANITO_PROVIDER = "azure"
$env:OPENAI_BASE_URL = "https://your-resource.openai.azure.com"
$env:OPENAI_MODEL = "your-deployment-name"
$env:OPENAI_API_KEY = "your-azure-key"

# Use the CLI
python -m janito4 "Your prompt here"
```

## Examples

### OpenAI API

```bash
export OPENAI_BASE_URL="https://api.openai.com"
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"
python -m janito4 "Explain quantum computing in simple terms"
```

### Local LLM (e.g., LM Studio, Ollama)

```bash
export OPENAI_BASE_URL="http://localhost:1234/v1"  # LM Studio default
export OPENAI_API_KEY="not-needed"                 # Often not required for local servers
export OPENAI_MODEL="local-model-name"
python -m janito4 "What is 2+2?"
```

### Custom Provider (e.g., MiniMax)

```bash
export JANITO_PROVIDER="custom"
export OPENAI_BASE_URL="https://api.minimax.chat/minimax/v1"
export OPENAI_MODEL="MiniMax-M2.7"
export OPENAI_API_KEY="your-minimax-api-key"
python -m janito4 "Hello"
```

### Azure OpenAI

```bash
export JANITO_PROVIDER="azure"
export OPENAI_BASE_URL="https://your-resource.openai.azure.com"
export OPENAI_MODEL="your-deployment-name"
export OPENAI_API_KEY="your-azure-key"
python -m janito4 "Hello"
```

## Notes

- Environment variables take precedence over saved configuration
- For security, avoid hardcoding API keys in scripts; consider using a `.env` file with a tool like `python-dotenv`
- The `--set`, `--set-api-key`, and `--config` CLI options override environment variables at runtime
