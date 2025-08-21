# Configuring Janito for DeepSeek

Janito supports DeepSeek as an LLM provider. This guide explains how to configure Janito to use DeepSeek models.

## 1. Obtain a DeepSeek API Key

- Sign up or log in at [DeepSeek](https://deepseek.com/) to get your API key.

## 2. Set Your DeepSeek API Key in Janito

You must specify both the API key and the provider name when configuring Janito for DeepSeek:

```bash
janito --set-api-key YOUR_DEEPSEEK_API_KEY -p deepseek
```

Replace `YOUR_DEEPSEEK_API_KEY` with your actual DeepSeek API key.

## 3. Select DeepSeek as the Provider

You can set DeepSeek as your default provider:

```bash
janito --set provider=deepseek
```

Or specify it per command:

```bash
janito -p deepseek "Your prompt here"
```

## 4. Choose a DeepSeek Model

Janito supports the following DeepSeek models:

- `deepseek-chat` (default) - General purpose chat model (8K context)
- `deepseek-reasoner` - Specialized for complex reasoning tasks (8K context)
- `deepseek-v3.1` - Latest V3.1 model with 128K context window
- `deepseek-v3.1-base` - Base V3.1 model with 128K context window
- `deepseek-r1` - R1 model with 128K context window

To select a model:

```bash
janito -p deepseek -m deepseek-reasoner "Your prompt here"

# Or use the latest models:
janito -p deepseek -m deepseek-v3.1 "Your prompt here"
janito -p deepseek -m deepseek-r1 "Your prompt here"
```

## 5. Verify Your Configuration

Show your current configuration (the config file path will be shown at the top):

```bash
janito --show-config
```

## 6. Troubleshooting

- Ensure your API key is correct and active.
- If you encounter issues, use `janito --list-providers` to verify DeepSeek is available.
- For more help, see the main [Configuration Guide](guides/configuration.md) or run `janito --help`.

---

For more details on supported models and features, see [Supported Providers & Models](supported-providers-models.md).
