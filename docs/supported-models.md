# Supported Models

> 🚀 **Janito is optimized and tested for the default model: `openai/gpt-4.1`.**
> 🧪 Testing and feedback for other models is welcome!

## 🌐 Providers

- 🧩 **Bring your own model using the OpenAI-compatible API!**

- 🟢 **OpenRouter** (default)
- 🟦 **OpenAI** (api.openai.com)
- 🟪 **Azure OpenAI**

## 🤖 Model Types

Janito is compatible with most OpenAI-compatible chat models, including but not limited to:

- `openai/gpt-4.1` (default)
- Any model available via OpenRouter (Anthropic, Google, Mistral, etc.)
- Azure-hosted OpenAI models (with correct deployment name)

## 🛠️ How to Select a Model

- Use the `--model` CLI option to specify the model for a session:
  ```
  janito "Prompt here" --model openai/gpt-4.1
  ```
- Configure your API key and endpoint in the configuration file or via CLI options.

## ℹ️ Notes

- Some advanced features (like tool calling) require models that support OpenAI function calling.
- Model availability and pricing depend on your provider and API key.
- For the latest list of supported models, see your provider’s documentation or the [OpenRouter models page](https://openrouter.ai/models).
