# Configuration

Janito's behavior is controlled through a combination of environment variables, configuration files, and CLI commands.

## Configuration Sources (Priority Order)

1. **Command-line arguments** (highest priority)
2. **Environment variables**
3. **Configuration file** (`~/.janito/config.yaml`)
4. **Default values** (lowest priority)

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `MISTRAL_API_KEY` | Mistral API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `CEREBRAS_API_KEY` | Cerebras API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `ZAI_API_KEY` | Z.AI API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `ALIBABA_API_KEY` | Alibaba Qwen API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `DEEPSEEK_API_KEY` | DeepSeek API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `MOONSHOT_API_KEY` | Moonshot API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `WATSONX_API_KEY` | IBM WatsonX API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `WATSONX_PROJECT_ID` | IBM WatsonX project ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `WATSONX_SPACE_ID` | IBM WatsonX space ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `JANITO_PROVIDER` | Default provider | `openai` |

## Configuration File

The configuration file is located at `~/.janito/config.yaml` and has the following structure:

```yaml
provider: openai
azure_deployment_name: my-deployment
max_tokens: 4096
default_temperature: 0.7
enable_tools: true
```

You can modify this file directly or use the CLI:

```bash
# Set default provider
janito set-config provider=openai

# Set Azure deployment name
janito set-config azure_deployment_name=my-deployment

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
- **Cerebras**: `qwen-3-coder-480b`
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

### Model@Provider Syntax

For convenience, you can specify both model and provider in a single argument using the `model@provider` syntax:

```bash
# These are equivalent:
janito chat --provider openai --model gpt-4o
janito chat -m gpt-4o@openai

# More examples:
janito -m claude-sonnet-4-5-20250929@anthropic "Write a Python function"
janito -m kimi-k1-8k@moonshot "Translate this to Chinese"
janito -m deepseek-chat@deepseek "Explain machine learning"
```

This syntax is particularly useful for:
- Quick one-off commands
- Scripts and automation
- Following conventions from tools like Docker

> **Note**: If you specify both `-m model@provider` and `-p provider`, the explicit `-p` flag takes precedence.

> **Note**: The list of available models is automatically synchronized with the codebase. Use `janito list-models --provider PROVIDER` to see all available options.