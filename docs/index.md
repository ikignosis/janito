# Welcome to Janito

Janito is a flexible and extensible platform for interacting with large language models (LLMs) from multiple providers.

## Key Features

- **Multi-provider support**: Access models from OpenAI, Anthropic, Google Gemini, Mistral, Alibaba Qwen, Z.AI, DeepSeek, Moonshot, IBM WatsonX, and Azure OpenAI
- **Unified interface**: Consistent CLI and API across all providers
- **Tool integration**: Built-in tools for file management, web access, code execution, and more
- **Plugin system**: Extend functionality with modular plugins
- **Security first**: Permission controls and sandboxed operations
- **Automatic documentation**: Supported models are automatically synchronized with the codebase

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

## Quick Examples

```bash
# Simple prompt
janito "Create a Python script to calculate fibonacci numbers"

# Using specific model and provider
janito -p openai -m gpt-4 "Explain quantum computing"

# Using the shorthand model@provider syntax
janito -m gpt-4@openai "Explain quantum computing"

# Interactive mode
janito --interactive
```

## Documentation

Explore our comprehensive documentation:

- [Installation & Setup](guides/installation.md)
- [Configuration](configuration.md)
- [CLI Commands](cli.md)
- [Supported Models](models/supported_models.md)
- [Tools & Plugins](tools.md)
- [Developer Guide](guides/developing.md)

> **Note**: The list of supported models is automatically generated from the codebase. When new models are added, this documentation updates automatically.*