# Configuration

Learn how to configure janito for your needs.

## Topics

- [Providers](providers.md) - Configure OpenAI, local servers, or custom providers
- [Environment Variables](environment-variables.md) - Use environment variables for configuration
- [Secrets](secrets.md) - Manage API keys and sensitive credentials

## Configuration File

janito stores your configuration in `~/.janito/`. The main configuration file is `~/.janito/config.json`.

### View Configuration

```bash
janito --show-config
```

### Configuration Options

These keys are stored in `~/.janito/config.json` (set them with `--set`):

| Option | Description | Default |
|--------|-------------|---------|
| `provider` | Provider name (`openai`, `custom`, `alibaba`, `minimax`, `xiaomi`, `moonshot`, `zai`) | `openai` |
| `model` | Model name | - |
| `context-window-size` | Maximum context window size (tokens) | `65536` |
| `endpoint` | API endpoint URL (required for `custom` providers) | - |

> Provider base URLs are built in for known providers, so you normally only need `endpoint` for the `custom` provider. At runtime the endpoint is exported as the `OPENAI_BASE_URL` environment variable.

## Configuration Priority

For `model` and `endpoint`, values are resolved in this order (later overrides earlier):

1. Default values
2. Configuration file (`~/.janito/config.json`)
3. Environment variables (`OPENAI_MODEL`, `OPENAI_BASE_URL`)
4. Command-line arguments (`--model`, `--endpoint`)

API keys are resolved from the `OPENAI_API_KEY` environment variable first, then from the per-provider key stored in `~/.janito/auth.json` (set with `--set-api-key`).

> **Note:** When using CLI arguments, `--set` and `--set-api-key` must be run as **separate commands**. They cannot be combined in a single invocation.

## Next Steps

- [Configure providers](providers.md) for different AI services
- [Set up environment variables](environment-variables.md) for automation
- [Manage secrets](secrets.md) securely
