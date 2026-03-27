# Environment Variables

Configure janito using environment variables for automation and scripting.

## Available Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_BASE_URL` | Base URL of the OpenAI-compatible API | `https://api.openai.com` |
| `OPENAI_API_KEY` | API key for authentication | `sk-xxxxxxxx...` |
| `OPENAI_MODEL` | Model name/deployment name | `gpt-4` |
| `JANITO_PROVIDER` | Provider type | `openai`, `custom` |

## Unix/Linux/macOS

### Bash

```bash
# For OpenAI
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_MODEL="gpt-4"

# For local servers
export OPENAI_BASE_URL="http://localhost:1234/v1"
export OPENAI_API_KEY="not-needed"
export OPENAI_MODEL="local-model"

# For custom providers
export JANITO_PROVIDER="custom"
export OPENAI_BASE_URL="http://localhost:8000/minimax/v1"
export OPENAI_MODEL="MiniMax-M2.7"
export OPENAI_API_KEY="your-api-key"
```

### Zsh

Same as Bash. Add to `~/.zshrc`:

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4"
```

## Windows

### PowerShell

```powershell
# For OpenAI
$env:OPENAI_API_KEY = "sk-your-openai-key"
$env:OPENAI_MODEL = "gpt-4"

# For local servers
$env:OPENAI_BASE_URL = "http://localhost:1234/v1"
$env:OPENAI_API_KEY = "not-needed"
$env:OPENAI_MODEL = "local-model"
```

### Command Prompt (cmd)

```cmd
set OPENAI_API_KEY=sk-your-key
set OPENAI_MODEL=gpt-4
```

## Examples

### OpenAI API

```bash
export OPENAI_BASE_URL="https://api.openai.com"
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4"
janito "Explain quantum computing"
```

### Local LLM (LM Studio, Ollama)

```bash
export OPENAI_BASE_URL="http://localhost:1234/v1"
export OPENAI_API_KEY="not-needed"
export OPENAI_MODEL="local-model-name"
janito "What is 2+2?"
```

### Custom Provider (MiniMax)

```bash
export JANITO_PROVIDER="custom"
export OPENAI_BASE_URL="https://api.minimax.chat/minimax/v1"
export OPENAI_MODEL="MiniMax-M2.7"
export OPENAI_API_KEY="your-api-key"
janito "Hello"
```

## Using .env Files

For better security, store your API keys in a `.env` file and load them with `python-dotenv`:

### Install python-dotenv

```bash
pip install python-dotenv
```

### Create .env file

```bash
# .env
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4
```

### Load in your script

```bash
# Load environment variables
export $(cat .env | xargs)

# Or use python-dotenv
python -c "from dotenv import load_dotenv; load_dotenv()"

# Run janito
janito "Hello"
```

!!! warning "Security Note"
    Never commit `.env` files to version control. Add `.env` to your `.gitignore`.

## Notes

- Environment variables take precedence over saved configuration
- The `--set` and `--config` CLI options override environment variables at runtime
- For security, avoid hardcoding API keys in scripts
