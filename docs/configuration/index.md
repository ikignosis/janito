# Configuration

Learn how to configure janito for your needs.

## Topics

- [Providers](providers.md) - Configure OpenAI, local servers, or custom providers
- [Secrets](secrets.md) - Manage API keys and sensitive credentials

## Configuration File

janito stores your configuration in `~/.janito/`. The main configuration file is `~/.janito/config.json`.

> **Custom config directory:** Use `-c`/`--config-dir <dir>` to store *all* config
> (config, auth, secrets, MCP services and skills) in a different directory
> instead of `~/.janito`. For example: `janito -c ~/myconf --set provider=openai`.

### View Configuration

```bash
janito --show-config
```

### Configuration Options

These keys are stored in `~/.janito/config.json` (set them with `--set`):

| Option | Description | Default |
|--------|-------------|---------|
| `provider` | Provider name (`openai`, `custom`, `alibaba`, `minimax`, `xiaomi`, `moonshot`, `zai`, `xai`) | `openai` |
| `model` | Model name | - |
| `context-window-size` | Maximum context window size (tokens) | `65536` |
| `endpoint` | API endpoint URL (required for `custom` providers) | - |

> Provider base URLs are built in for known providers, so you normally only need `endpoint` for the `custom` provider. At runtime the endpoint is used directly as the API base URL.

## Configuration Priority

Configuration is resolved from local files — janito does **not** read any
`OPENAI_*` environment variables. Values are resolved in this order (later
overrides earlier):

1. Provider's built-in default (endpoint) / no default (model)
2. Configuration file (`~/.janito/config.json`)
3. Command-line arguments (`--model`, `--provider`, `--set endpoint=...`)

API keys are read from the per-provider key stored in `~/.janito/auth.json`
(set with `--set-api-key <key> --provider <name>`). There is no environment
variable fallback.

> **Note:** When using CLI arguments, `--set` and `--set-api-key` must be run as **separate commands**. They cannot be combined in a single invocation.

> **Note:** If an API key is already stored for a provider, `--set-api-key` warns you and asks for confirmation before overwriting it. Pass `-f`/`--force` to overwrite without prompting (useful for scripts and non-interactive use).

## Next Steps

- [Configure providers](providers.md) for different AI services
- [Manage secrets](secrets.md) securely
