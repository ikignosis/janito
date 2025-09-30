# Anthropic Setup

To use Anthropic models with Janito, follow these steps:

## 1. Get Your API Key

1. Sign up at [https://console.anthropic.com/](https://console.anthropic.com/)
2. Navigate to your API keys page
3. Create a new API key or copy an existing one

## 2. Set the API Key

Set your Anthropic API key using the CLI:

```bash
janito set-api-key --provider anthropic --key YOUR_API_KEY_HERE
```

Or set it as an environment variable:

```bash
export ANTHROPIC_API_KEY="YOUR_API_KEY_HERE"
```

## 3. Available Models

Janito supports the following Anthropic models:

- `claude-sonnet-4-5-20250929` - Latest model with enhanced agent and coding capabilities
- `claude-opus-4-1-20250805` - Exceptional model for specialized complex tasks
- `claude-opus-4-20250514` - High-capability model for complex tasks
- `claude-sonnet-4-20250514` - Balanced performance and cost
- `claude-3-7-sonnet-20250219` - High-performance model
- `claude-3-5-haiku-20241022` - Fast and cost-effective
- `claude-3-5-sonnet-20241022` - Balanced speed and capability
- `claude-3-haiku-20240307` - Fastest model for simple tasks

## 4. Usage Examples

### List available models

```bash
janito list-models --provider anthropic
```

### Use a specific model

```bash
janito chat --provider anthropic --model claude-3-5-sonnet-20241022
```

### Set as default provider

```bash
janito set-config provider=anthropic
```

## Notes

- Anthropic is accessed through an OpenAI-compatible API endpoint
- The default model is `claude-sonnet-4-5-20250929`
- All models support streaming responses
- Context window sizes vary by model (see [Supported Models](models/supported_models.md) for details)

For more information, visit the [Anthropic documentation](https://docs.anthropic.com/).