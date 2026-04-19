# Alibaba (Qwen) Configuration

Connect janito to [Alibaba Cloud's DashScope API](https://dashscope.aliyuncs.com/) to use Qwen models.

## Prerequisites

1. Create an [Alibaba Cloud account](https://www.alibabacloud.com/)
2. Subscribe to the [DashScope service](https://dashscope.console.aliyun.com/)
3. Generate an API key from the [API Key management page](https://dashscope.console.aliyun.com/apiKey)

## Quick Setup

```bash
janito --set provider=alibaba \
       --set model="qwen-plus" \
       --set-api-key="sk-your-alibaba-api-key"
```

The base URL (`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`) is automatically resolved — no need to set `--endpoint`.

## Available Models

| Model | Description | Context Window |
|-------|-------------|----------------|
| `qwen-turbo` | Fast, cost-effective | 8K / 100K (extended) |
| `qwen-plus` | Balanced performance | 8K / 130K (extended) |
| `qwen-max` | Highest capability | 8K / 130K (extended) |
| `qwen-long` | Long document processing | 100K |
| `qwen-vl-max` | Vision-language (multimodal) | 7.5K |
| `qwen-vl-plus` | Vision-language (multimodal) | 7.5K |
| `qwen3.6-flash` | Advanced reasoning with thinking mode | Varies |

## Preserve Thinking Mode

For Qwen models that support extended thinking/reasoning (such as **qwen3.6-flash**), you can enable the `preserve_thinking` option:

### Via Command Line

Set the config value alongside your Alibaba config:

```bash
janito --set provider=alibaba \
       --set model="qwen3.6-flash" \
       --set preserve_thinking=true \
       --set-api-key="sk-your-alibaba-api-key"
```

### Via Interactive Config

```bash
janito --config
```

Answer the prompts, then set `preserve_thinking` directly in the config file located at:

```
~/.janito/config.json        # Linux/macOS
%USERPROFILE%\.janito\config.json   # Windows
```

Add the key manually:

```json
{
    "provider": "alibaba",
    "model": "qwen3.6-flash",
    "api_key": "sk-your-alibaba-api-key",
    "preserve_thinking": true
}
```

### Environment Variables

```bash
export JANITO_PROVIDER="alibaba"
export OPENAI_API_KEY="sk-your-alibaba-api-key"
export OPENAI_MODEL="qwen3.6-flash"
export PRESERVE_THINKING="true"
```

## Example Usage

```bash
# Set up once
janito --set provider=alibaba \
       --set model="qwen-plus" \
       --set-api-key="sk-your-alibaba-api-key" \
       --set preserve_thinking=true

# Start chatting
janito
```

## Troubleshooting

### Invalid API Key

- Verify your key on the [DashScope console](https://dashscope.console.aliyun.com/apiKey)
- Ensure the key has access to the models you're trying to use
- Some models may require separate subscription

### Endpoint Errors

- The built-in `alibaba` provider uses `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- If you need the China mainland endpoint instead, switch to `custom` provider:
  ```bash
  janito --set provider=custom \
         --set endpoint="https://dashscope.aliyuncs.com/compatible-mode/v1"
  ```

### Model Not Found

- Check the [available models list](https://help.aliyun.com/zh/model-studio/getting-started/models)
- Ensure the model name matches exactly (e.g., `qwen-plus`, not `Qwen-Plus`)
