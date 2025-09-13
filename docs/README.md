# Janito LLM Platform Documentation

Welcome to the official documentation for Janito, a flexible and extensible platform for interacting with large language models (LLMs) from multiple providers.

## Table of Contents

- [Supported Models](models/supported_models.md)
- [Providers](providers.md)
- [CLI Commands](cli.md)
- [Configuration](configuration.md)
- [Tools & Plugins](tools.md)

## Overview

Janito provides a unified interface to access state-of-the-art LLMs from providers such as OpenAI, Anthropic, Google Gemini, Mistral, Alibaba Qwen, Z.AI, DeepSeek, Moonshot, IBM WatsonX, and Azure OpenAI.

All model specifications are automatically synchronized with the codebase. To see the latest supported models, visit the [Supported Models](models/supported_models.md) page.

## Getting Started

1. Install Janito:
   ```bash
   pip install janito
   ```

2. Set your API key:
   ```bash
   janito set-api-key --provider openai --key YOUR_API_KEY
   ```

3. List available models:
   ```bash
   janito list-models --provider openai
   ```

4. Start interactive chat:
   ```bash
   janito chat
   ```

For detailed usage, refer to the linked guides above.