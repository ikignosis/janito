# Providers

janito supports multiple AI providers. This guide covers configuration for each.

## Supported Providers

| Provider | Type | Description |
|----------|------|-------------|
| `openai` | Standard | OpenAI API (default) |
| `custom` | Custom | Any OpenAI-compatible API (local servers, third-party) |
| `alibaba` | Third-party | [Alibaba Cloud DashScope](https://dashscope.aliyuncs.com/) (Qwen models) |

## OpenAI

### Configuration

```bash
janito --set provider=openai --set-api-key="sk-your-key" --set model=gpt-4
```

Or interactively:

```bash
janito --config
```

### Environment Variables

```bash
export OPENAI_API_KEY="sk-your-key"
export OPENAI_MODEL="gpt-4"
```

## Custom Providers (OpenAI-Compatible)

Use any OpenAI-compatible API, including local servers like LM Studio, Ollama, or third-party providers.

### Configuration

```bash
janito --set provider=custom --set endpoint="http://localhost:8000/v1" --set model="my-model" --set-api-key="optional-key"
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
| **Alibaba (Qwen)** | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

For full Alibaba/Qwen setup with `preserve_thinking` examples, see [Alibaba Configuration](alibaba.md).

### Example: LM Studio

```bash
janito --set provider=custom \
        --set endpoint="http://localhost:1234/v1" \
        --set model="local-model-name" \
        --set-api-key="not-needed" \
        "Hello"
```

## Provider Comparison

| Feature | OpenAI | Custom |
|---------|--------|--------|
| Function Calling | ✅ | Depends on API |
| Streaming | ✅ | Depends on API |
| Vision | ✅ | Depends on API |
| Context Window | Up to 128k | Varies |

## Troubleshooting

### Connection Errors

- Verify the endpoint URL is correct (including `/v1` suffix)
- Check firewall settings
- Ensure the server is running (for local servers)

### Authentication Errors

- Verify your API key is correct
- Check if the API key has the necessary permissions
- Some local servers don't require an API key - try `--set-api-key="not-needed"`
