# Configuration

Janito's behavior is controlled through a combination of environment variables, configuration files, and CLI commands.

## Configuration Sources (Priority Order)

1. **Command-line arguments** (highest priority)
2. **Configuration file** (`~/.janito/config.json`)
3. **Default values** (lowest priority)

## Environment Variables

> **Note**: API keys are set via `janito --set-api-key YOUR_KEY -p PROVIDER` and stored in `~/.janito/auth.json`. Provider-specific API key environment variables are not supported.

| Variable | Description | Example |
|----------|-------------|---------|
| `BASE_URL` | Custom API base URL (overrides provider default) | `https://api.example.com` |
| `BASE_API_KEY` | Custom API key (overrides provider-specific API key) | `sk-...` |

## Configuration File

The configuration file is located at `~/.janito/config.json` and has the following structure:

```json
{
  "provider": "openai",
  "model": "gpt-5",
  "base_url": null
}
```

You can modify this file directly or use the CLI:

```bash
# Set default provider
janito set-config provider=openai

# Set Azure deployment name
janito set-config azure_deployment_name=my-deployment

# Set custom base URL
janito set-config base_url=https://api.example.com

# View current config
janito show-config
```

## Provider-Specific Configuration

### Azure OpenAI

For Azure OpenAI, you must specify your deployment name:

```bash
janito set-config azure_deployment_name=my-gpt4o-deployment
```

This maps to the `--model` parameter in CLI commands:

```bash
janito chat --provider azure_openai
# Internally uses model: my-gpt4o-deployment
```

### IBM WatsonX

For IBM WatsonX, you need both API key and project ID:

```bash
janito set-config watsonx_project_id=your-project-id
janito set-config watsonx_space_id=your-space-id
```

## Model Selection

When no model is specified, Janito uses the provider's default model:

- **OpenAI**: `gpt-5`
- **Anthropic**: `claude-sonnet-4-5-20250929`
- **Google**: `gemini-2.5-flash`
- **Mistral**: `mistral-large-latest`

- **Z.AI**: `glm-4.5`
- **Alibaba**: `qwen3-next-80b-a3b-instruct`
- **DeepSeek**: `deepseek-chat`
- **Moonshot**: `kimi-k2-0905-preview`
- **IBM WatsonX**: `ibm/granite-3-3-8b-instruct`
- **Azure OpenAI**: `azure_openai_deployment`

You can override the default model using `--model MODEL_NAME` on any command:

```bash
janito chat --provider openai --model gpt-4o
```

### Base URL Configuration

You can configure a custom base URL for API endpoints in two ways:

1. Using the `BASE_URL` environment variable (highest priority):
   ```bash
   BASE_URL=https://api.example.com janito chat
   ```

2. Using the configuration file:
   ```bash
   janito set-config base_url=https://api.example.com
   ```

The `BASE_URL` environment variable takes precedence over the configuration file setting.

### Model@Provider Syntax

For convenience, you can specify both model and provider in a single argument using the `model@provider` syntax:

```bash
# These are equivalent:
janito chat --provider openai --model gpt-4o
janito chat -m gpt-4o@openai

# More examples:
janito -m claude-sonnet-4-5-20250929@anthropic "Write a Python function"
janito -m kimi-k2-thinking@moonshot "Translate this to Chinese"
janito -m deepseek-chat@deepseek "Explain machine learning"
```

This syntax is particularly useful for:
- Quick one-off commands
- Scripts and automation
- Following conventions from tools like Docker

> **Note**: If you specify both `-m model@provider` and `-p provider`, the explicit `-p` flag takes precedence.

> **Note**: The list of available models is automatically synchronized with the codebase. Use `janito list-models --provider PROVIDER` to see all available options.