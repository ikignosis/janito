# Cerebras Setup Guide

This guide will help you set up Janito to use Cerebras as an LLM provider.

## Prerequisites

1. A Cerebras account
2. An API key from Cerebras

## Getting an API Key

1. Visit the [Cerebras API Keys page](https://api.cerebras.ai/)
2. Log in to your account
3. Generate a new API key
4. Copy the API key for use in Janito

## Configuration

To configure Janito to use Cerebras, you need to set your API key:

```bash
janito --set-api-key YOUR_CEREBRAS_API_KEY -p cerebras
```

Replace `YOUR_CEREBRAS_API_KEY` with the API key you obtained from Cerebras.

## Usage

After setting up your API key, you can use Cerebras models with Janito:

```bash
janito -p cerebras "Hello, how are you?"
```

By default, Janito will use the `qwen-3-coder-480b` model. You can specify a different model if needed:

```bash
janito -p cerebras -m qwen-3-coder-480b "Explain quantum computing"
```

## Available Models

Cerebras offers several models through their API:

**Production Models:**

- `llama-4-scout-17b-16e-instruct`
- `llama-3.3-70b`
- `llama3.1-8b`
- `qwen-3-32b`

**Preview Models:**

- `llama-4-maverick-17b-128e-instruct`
- `qwen-3-235b-a22b-instruct-2507`
- `qwen-3-235b-a22b-thinking-2507`
- `qwen-3-coder-480b`
- `gpt-oss-120b`

**Notes:**

- `qwen-3-coder-480b`: 32k context, reasoning-focused model with function calling support

## Troubleshooting

If you encounter issues:

1. Verify your API key is correct and active
2. Check that you have internet connectivity
3. Ensure you're using a supported model name
4. Check the Cerebras status page for any service outages

For further assistance, consult the [Cerebras documentation](https://api.cerebras.ai/docs) or [Janito documentation](https://docs.janito.dev).