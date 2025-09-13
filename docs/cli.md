# CLI Commands

Janito provides a comprehensive command-line interface (CLI) for managing and interacting with LLM providers.

## Core Commands

### `list-models`

List all supported models for a given provider.

```bash
# List models for OpenAI
janito list-models --provider openai

# List models for the default provider
janito list-models
```

### `list-providers`

List all available providers and their status.

```bash
janito list-providers
```

### `set-api-key`

Set your API key for a specific provider.

```bash
janito set-api-key --provider openai --key sk-your-key-here
```

### `chat`

Start an interactive chat session with the default model.

```bash
janito chat
```

### `show-config`

Display current configuration settings.

```bash
janito show-config
```

### `ping-providers`

Test connectivity to all providers.

```bash
janito ping-providers
```

## Provider-Specific Commands

### `list-providers-region`

List providers available in a specific region.

```bash
janito list-providers-region --region us-east-1
```

### `list-tools`

List all available tools and plugins.

```bash
janito list-tools
```

## Configuration Commands

### `set-config`

Set a configuration value.

```bash
janito set-config provider=openai
janito set-config azure_deployment_name=my-deployment
```

### `show-config`

Show current configuration.

```bash
janito show-config
```

### `unset-config`

Remove a configuration value.

```bash
janito unset-config provider
```

## Advanced Commands

### `model-selection`

Interactively select a model from available options.

```bash
janito model-selection
```

### `enable-plugin` / `disable-plugin`

Enable or disable a plugin.

```bash
janito enable-plugin webtools
janito disable-plugin filemanager
```

For detailed help on any command, use:

```bash
janito COMMAND --help
```

> **Note**: The `list-models` command automatically reflects the latest model specifications defined in the codebase. No manual documentation update is required when new models are added.