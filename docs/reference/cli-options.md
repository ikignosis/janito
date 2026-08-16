# CLI Options

Complete reference for janito command-line options.

## Usage

```bash
janito [options] [prompt]
```

If no prompt is given, janito starts an interactive chat shell.

## Prompt

| Argument | Description |
|----------|-------------|
| `prompt` | The prompt to send to the AI. If omitted, interactive chat starts. |

## Configuration

| Option | Description |
|--------|-------------|
| `-c`, `--config-dir <dir>` | Directory for all janito config (config, auth, secrets, MCP, skills). Defaults to `~/.janito` |
| `-l`, `--local` | Use the project-local config directory `./.janito` (the current working directory) for `--set`, `--set-api-key`, `--set-secret`, etc. Reads resolve local values first and fall back to the global `~/.janito`; list operations show both |
| `--config` | Open the interactive configuration wizard |
| `--show-config` | Display the configured provider and model |
| `--info` | Print resolved configuration (provider, model, API key) and exit |
| `--set <key=value>` | Set one or more config values in `~/.janito/config.json` |
| `--unset <key>` | Remove one or more config keys from `~/.janito/config.json` |
| `--get <key>` | Get one or more config values from `~/.janito/config.json` |
| `--set-api-key <key>` | Set the API key for a provider. Uses `--provider`, or falls back to the configured default provider (`--set provider=<name>`) when `--provider` is omitted; errors if neither is available. If a key is already stored, janito warns and prompts for confirmation before overwriting; use `-f`/`--force` to overwrite without prompting. |
| `-f`, `--force` | Overwrite an existing API key without prompting (used with `--set-api-key`) |
| `--provider <name>` | Provider name (e.g., `openai`, `custom`). Always validated against the supported providers; unknown names are rejected. |
| `--model <name>` | Model name (overrides the provider's configured model) |
| `--list-keys` | List configured providers and keys (with `-l`/`--local`, shows both the local and the global auth files) |
| `--show-providers` | List all supported providers and their built-in defaults (model, API types, endpoint, token limits, thinking/reasoning, built-in tools per API type), followed by the registered provider variants |

> **Note:** `--set` and `--set-api-key` must be used in **separate commands**, not together on the same line.

## Provider Variants

| Option | Description |
|--------|-------------|
| `--create-variant <name>` | Register a provider variant `<provider>-<word>` (e.g. `alibaba-tokenplan`) in `config.json`. After creation the name behaves like any provider (`--provider`, `--set provider=`, `--set-api-key`), inheriting its base provider's built-in defaults with its own per-variant model/endpoint/API key |
| `--delete-variant <name>` | Delete a provider variant and its per-variant configuration (model, endpoint, API type, tokens, reasoning level, API key). Refuses to delete the configured default provider |

```bash
janito --create-variant alibaba-tokenplan
janito --provider alibaba-tokenplan --set model=qwen-plus
janito --set-api-key sk-xxx --provider alibaba-tokenplan
janito --set provider=alibaba-tokenplan
janito --delete-variant alibaba-tokenplan
```

See [Provider Variants](../configuration/variants.md) for the full guide.

## Secrets

| Option | Description |
|--------|-------------|
| `--set-secret <key=value>` | Set one or more secrets in `~/.janito/secrets.json` |
| `--get-secret <key>` | Get one or more secret values |
| `--delete-secret <key>` | Delete one or more secrets |
| `--list-secrets` | List all configured secret keys (with `-l`/`--local`, shows both the local and the global secrets files) |

## System Prompt

| Option | Description |
|--------|-------------|
| `-Z`, `--no-system-prompt` | Do not set a system prompt and do not pass any tools |
| `-S`, `--system-prompt <prompt>` | Override the system prompt (tools stay enabled) |
| `--no-tools` | Do not load tools (skill tools stay enabled) |
| `--show-system-prompt` | Display the resolved system prompt and exit |
| `-t`, `--thinking` | Enable thinking mode (sends `extra_body={'enable_thinking': True}`). DeepSeek, Alibaba/Qwen and MiniMax-M3 have thinking enabled by default |
| `--reasoning-level <level>` | Set the reasoning depth for the API call (sends `reasoning_effort=<level>`). Overrides the provider's configured value and built-in default. Values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. |

## Privileges

| Option | Description |
|--------|-------------|
| `-r`, `--read` | Grant READ privilege |
| `-w`, `--write` | Grant WRITE privilege |
| `-x`, `--exec` | Grant EXEC privilege |

If none of `-r`, `-w`, `-x` are given, janito runs with full privileges and prints a warning.

## Tools

| Option | Description |
|--------|-------------|
| `--gmail` | Enable Gmail tools and the email-specific system prompt |
| `--onedrive` | Enable OneDrive tools and the file-specific system prompt |
| `--onedrive-auth` | Authenticate with Microsoft OneDrive (device code flow) |
| `--onedrive-status` | Show OneDrive authentication status |
| `--onedrive-logout` | Clear OneDrive authentication tokens |
| `--list-tools` | List all available built-in tools and exit |

## Skills

| Option | Description |
|--------|-------------|
| `--install-skill <url>` | Install a skill from a GitHub URL |
| `--list-skills` | List all installed skills |
| `--uninstall-skill <name>` | Uninstall a skill by name |

## MCP

| Option | Description |
|--------|-------------|
| `--list-mcp` | List all MCP services and their tools |

## Logging & Output

| Option | Description |
|--------|-------------|
| `--log=<levels>` | Enable logging (e.g., `--log=info,debug` or `--log=warning,error`) |
| `-v`, `--verbose` | Enable verbose output (shows model and backend info) |
| `--no-history` | Don't persist interactive input history to file |
| `--version` | Show version information and exit |
| `--help` | Show help message and exit |

## Examples

### Configure

```bash
janito --config
janito --show-config
janito --info
janito --show-providers   # list every provider and variant with its defaults
janito --set provider=openai --set model=gpt-4
janito --set-api-key sk-your-key --provider openai
janito --set-api-key sk-your-key   # uses the configured default provider
```

### Project-local configuration

With `-l`/`--local`, configuration is stored in `./.janito` (the current
working directory) instead of `~/.janito`. Reads resolve local values first
and fall back to the global directory, and `--list-keys` / `--list-secrets`
show both:

```bash
janito -l --set model=gpt-4                  # store config in ./.janito
janito -l --set-api-key sk-your-key --provider openai   # store the key in ./.janito
janito -l --list-keys                        # show global and local keys
```

### Secrets

```bash
janito --set-secret gmail_username=user@gmail.com
janito --set-secret gmail_password="xxxx xxxx xxxx xxxx"
janito --get-secret gmail_username
janito --list-secrets
janito --delete-secret gmail_password
```

### Enable Tools

```bash
janito --gmail "Show my emails"
janito --onedrive "List files"
janito --list-tools
```

### System Prompt & Privileges

```bash
janito -Z "Simple prompt without tools"
janito -S "You are a concise coding assistant" "Explain recursion"
janito -r -w "Refactor this file"
```

### Logging

```bash
janito --log=info "prompt"
janito --log=debug "prompt"
janito --log=info,debug "prompt"
```

## Configuration Keys

Values stored in `~/.janito/config.json` via `--set`:

| Key | Description | Default |
|-----|-------------|---------|
| `provider` | Provider name (`openai`, `custom`, `alibaba`, `minimax`, `xiaomi`, `moonshot`, `zai`, `xai`) | `openai` |
| `model` | Model name | - |
| `max-input-tokens` | Maximum input tokens (context window) | model built-in / `128000` |
| `max-output-tokens` | Maximum output tokens | model built-in / `100000` |
| `endpoint` | API endpoint URL (required for `custom` provider) | - |
