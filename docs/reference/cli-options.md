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
| `--config` | Open the interactive configuration wizard |
| `--show-config` | Display the configured provider and model |
| `--info` | Print resolved configuration (provider, model, API key) and exit |
| `--set <key=value>` | Set one or more config values in `~/.janito/config.json` |
| `--unset <key>` | Remove one or more config keys from `~/.janito/config.json` |
| `--get <key>` | Get one or more config values from `~/.janito/config.json` |
| `--set-api-key <key>` | Set the API key for a provider (requires `--provider`) |
| `--provider <name>` | Provider name (e.g., `openai`, `custom`) |
| `--model <name>` | Model name (overrides `OPENAI_MODEL` and config) |
| `--endpoint <url>` | API endpoint URL (required for `custom`, or overrides a provider base URL) |
| `--list-keys` | List configured providers and keys |

> **Note:** `--set` and `--set-api-key` must be used in **separate commands**, not together on the same line.

## Secrets

| Option | Description |
|--------|-------------|
| `--set-secret <key=value>` | Set one or more secrets in `~/.janito/secrets.json` |
| `--get-secret <key>` | Get one or more secret values |
| `--delete-secret <key>` | Delete one or more secrets |
| `--list-secrets` | List all configured secret keys |

## System Prompt

| Option | Description |
|--------|-------------|
| `-Z`, `--no-system-prompt` | Do not set a system prompt and do not pass any tools |
| `-S`, `--system-prompt <prompt>` | Override the system prompt (implies no tools) |
| `--show-system-prompt` | Display the resolved system prompt and exit |
| `-t`, `--thinking` | Enable thinking mode (sends `extra_body={'enable_thinking': True}`) |

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
janito --set provider=openai --set model=gpt-4
janito --set-api-key sk-your-key --provider openai
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
| `provider` | Provider name (`openai`, `custom`, `alibaba`, `minimax`, `xiaomi`, `moonshot`, `zai`) | `openai` |
| `model` | Model name | - |
| `context-window-size` | Maximum context window size (tokens) | `65536` |
| `endpoint` | API endpoint URL (required for `custom` provider) | - |
