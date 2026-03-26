# Configuration

Learn how to configure Janito4 for your needs.

## Topics

- [Providers](providers.md) - Configure OpenAI, local servers, or custom providers
- [Environment Variables](environment-variables.md) - Use environment variables for configuration
- [Secrets](secrets.md) - Manage API keys and sensitive credentials

## Configuration File

Janito4 stores your configuration in `~/.janito/`. The main configuration file is `~/.janito/config.json`.

### View Configuration

```bash
janito4 --show-config
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `provider` | Provider type (`openai`, `custom`) | `openai` |
| `model` | Model name | `gpt-4` |
| `context_window` | Maximum tokens | `65536` |
| `endpoint` | API endpoint URL (for custom providers) | - |
| `base_url` | Base URL for OpenAI-compatible APIs | `https://api.openai.com/v1` |

## Configuration Priority

Configuration values are loaded in this order (later overrides earlier):

1. Default values
2. Environment variables
3. Configuration file (`~/.janito/config.json`)
4. Command-line arguments (`--set`, `--set-api-key`)

## Next Steps

- [Configure providers](providers.md) for different AI services
- [Set up environment variables](environment-variables.md) for automation
- [Manage secrets](secrets.md) securely
