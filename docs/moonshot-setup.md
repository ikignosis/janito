# Configuring Janito for Moonshot

Janito supports Moonshot as an LLM provider. This guide explains how to configure Janito to use Moonshot models.

## 1. Obtain a Moonshot API Key

- Sign up or log in at [Moonshot AI Platform](https://platform.moonshot.ai) to get your API key.
- Navigate to the API Keys section in your dashboard to create and manage your keys.

## 2. Set Your Moonshot API Key in Janito

You must specify both the API key and the provider name when configuring Janito for Moonshot:

```bash
janito --set-api-key YOUR_MOONSHOT_API_KEY -p moonshot
```

Replace `YOUR_MOONSHOT_API_KEY` with your actual Moonshot API key.

## 3. Select Moonshot as the Provider

You can set Moonshot as your default provider:

```bash
janito --set provider=moonshot
```

Or specify it per command:

```bash
janito -p moonshot "Your prompt here"
```

## 4. Choose a Moonshot Model

Janito supports the following Moonshot models:

- `kimi-k2-turbo-preview` (default) - Advanced reasoning model with 128k context window
- `kimi-k2-turbo-preview` - Turbo version of the advanced reasoning model with 128k context window
- `kimi-k1-8k` - Standard model with 8k context window
- `kimi-k1-32k` - Standard model with 32k context window
- `kimi-k1-128k` - Standard model with 128k context window

To select a model:

```bash
janito -p moonshot -m kimi-k1-32k "Your prompt here"
```

## 5. Verify Your Configuration

Show your current configuration (the config file path will be shown at the top):

```bash
janito --show-config
```

## 6. API Endpoint Information

Moonshot uses an OpenAI-compatible API endpoint:

- **Base URL**: `https://api.moonshot.ai/v1`
- **Authentication**: Bearer token (API key)
- **Format**: OpenAI API format

## 7. Troubleshooting

- Ensure your API key is correct and has sufficient credits.
- If you encounter issues, use `janito --list-providers` to verify Moonshot is available.
- Check your API key permissions and rate limits in the Moonshot AI Platform dashboard.
- For more help, see the main [Configuration Guide](guides/configuration.md) or run `janito --help`.

---

For more details on supported models and features, see [Supported Providers & Models](supported-providers-models.md).