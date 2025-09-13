# Google Gemini Setup

To use Google Gemini models with Janito, follow these steps:

## 1. Get Your API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Generative Language API
4. Navigate to "APIs & Services" → "Credentials"
5. Create an API key

## 2. Set the API Key

Set your Google API key using the CLI:

```bash
janito set-api-key --provider google --key YOUR_API_KEY_HERE
```

Or set it as an environment variable:

```bash
export GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

## 3. Available Models

Janito supports the following Google Gemini models:

- `gemini-2.5-flash` - Fastest model for simple tasks
- `gemini-2.5-pro` - Most capable model for complex tasks
- `gemini-2.5-flash-lite-preview-06-17` - Lightweight version for low-latency applications

## 4. Usage Examples

### List available models

```bash
janito list-models --provider google
```

### Use a specific model

```bash
janito chat --provider google --model gemini-2.5-pro
```

### Set as default provider

```bash
janito set-config provider=google
```

## Notes

- Google Gemini is accessed through an OpenAI-compatible API endpoint
- The default model is `gemini-2.5-flash`
- All models support streaming responses and tool usage
- Context window sizes vary by model (see [Supported Models](models/supported_models.md) for details)

For more information, visit the [Google AI documentation](https://ai.google.dev/).