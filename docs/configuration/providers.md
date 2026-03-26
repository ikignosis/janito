# Providers

Janito4 supports multiple AI providers. This guide covers configuration for each.

## Supported Providers

| Provider | Type | Description |
|----------|------|-------------|
| `openai` | Standard | OpenAI API (default) |
| `anthropic` | Standard | Anthropic Claude API |
| `azure` | Azure | Microsoft Azure OpenAI |
| `custom` | Custom | Any OpenAI-compatible API |

## OpenAI

### Configuration

```bash
janito4 --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4
```

Or interactively:

```bash
janito4 --config
```

### Environment Variables

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4"
```

## Anthropic

### Configuration

```bash
janito4 --set provider=anthropic --set-api-key="sk-ant-api-key" --set model=claude-3-opus-20240229
```

### Environment Variables

```bash
export JANITO_PROVIDER="anthropic"
export OPENAI_API_KEY="sk-ant-api-key"
export OPENAI_MODEL="claude-3-opus-20240229"
```

## Azure OpenAI

### Configuration

```bash
janito4 --set provider=azure --set-api-key="your-azure-key" --set model="your-deployment-name"
```

### Environment Variables

```bash
export JANITO_PROVIDER="azure"
export OPENAI_BASE_URL="https://your-resource.openai.azure.com"
export OPENAI_API_KEY="your-azure-key"
export OPENAI_MODEL="your-deployment-name"
```

### Notes

- The `endpoint` or `OPENAI_BASE_URL` should point to your Azure OpenAI resource
- The `model` should be your deployment name in Azure
- Azure uses the same API format as OpenAI

## Custom Providers (OpenAI-Compatible)

Use any OpenAI-compatible API, including local servers like LM Studio, Ollama, or third-party providers.

### Configuration

```bash
janito4 --set provider=custom --set endpoint="http://localhost:8000/v1" --set model="my-model" --set-api-key="optional-key"
```

### Environment Variables

```bash
export JANITO_PROVIDER="custom"
export OPENAI_BASE_URL="http://localhost:8000/v1"
export OPENAI_API_KEY="optional-key"
export OPENAI_MODEL="my-model"
```

### Common Endpoints

| Provider | Endpoint Example |
|----------|------------------|
| LM Studio | `http://localhost:1234/v1` |
| Ollama | `http://localhost:11434/v1` |
| LocalAI | `http://localhost:8080/v1` |
| MiniMax | `https://api.minimax.chat/minimax/v1` |

### Example: LM Studio

```bash
janito4 --set provider=custom \
        --set endpoint="http://localhost:1234/v1" \
        --set model="local-model-name" \
        --set-api-key="not-needed" \
        "Hello"
```

## Provider Comparison

| Feature | OpenAI | Anthropic | Azure | Custom |
|---------|--------|-----------|-------|--------|
| Function Calling | ✅ | ✅ (Claude 3+) | ✅ | Depends on API |
| Streaming | ✅ | ✅ | ✅ | Depends on API |
| Vision | ✅ | ✅ | ✅ | Depends on API |
| Context Window | Up to 128k | Up to 200k | Up to 128k | Varies |

## Troubleshooting

### Connection Errors

- Verify the endpoint URL is correct (including `/v1` suffix)
- Check firewall settings
- Ensure the server is running (for local servers)

### Authentication Errors

- Verify your API key is correct
- Check if the API key has the necessary permissions
- Some local servers don't require an API key - try `--set-api-key="not-needed"`
