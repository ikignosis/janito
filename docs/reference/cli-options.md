# CLI Options

Complete reference for Janito4 command-line options.

## Usage

```bash
janito4 [options] [prompt]
```

## Options

### Configuration

| Option | Description |
|--------|-------------|
| `--config` | Open interactive configuration wizard |
| `--show-config` | Display current configuration |
| `--show-secrets` | Display current secrets (masked) |
| `--set <key=value>` | Set a configuration option |
| `--set-api-key <key>` | Set the API key |
| `--set-secret <key=value>` | Set a secret value |
| `--clear-secret <key>` | Clear a secret value |

### Providers

| Option | Description |
|--------|-------------|
| `--set provider=<provider>` | Set provider (`openai`, `custom`) |
| `--set model=<model>` | Set model name |
| `--set endpoint=<url>` | Set API endpoint URL |
| `--set context-window=<size>` | Set context window size |

### Tools

| Option | Description |
|--------|-------------|
| `--gmail` | Enable Gmail tools |
| `--gmail-auth` | Authenticate with Gmail |
| `--onedrive` | Enable OneDrive tools |
| `--onedrive-auth` | Authenticate with OneDrive |
| `--onedrive status` | Check OneDrive auth status |
| `--onedrive logout` | Log out from OneDrive |

### Logging

| Option | Description |
|--------|-------------|
| `--log=<level>` | Set log level (`info`, `debug`, `error`, `warning`) |

### Other

| Option | Description |
|--------|-------------|
| `--version` | Show version information |
| `--help` | Show help message |

## Examples

### Configure

```bash
janito4 --config
janito4 --show-config
janito4 --set provider=openai --set model=gpt-4
```

### Set Secrets

```bash
janito4 --set-secret gmail_username=user@gmail.com
janito4 --set-secret gmail_password=xxxx xxxx xxxx xxxx
janito4 --set-secret azure_client_id=xxx-xxx
janito4 --clear-secret gmail_password
```

### Enable Tools

```bash
janito4 --gmail "Show my emails"
janito4 --onedrive "List files"
janito4 --onedrive status
```

### Logging

```bash
janito4 --log=info "prompt"
janito4 --log=debug "prompt"
janito4 --log=info,debug "prompt"
```

## Configuration Keys

| Key | Description | Default |
|-----|-------------|---------|
| `provider` | Provider type | `openai` |
| `model` | Model name | `gpt-4` |
| `context_window` | Context window size | `65536` |
| `endpoint` | API endpoint URL | - |
| `base_url` | Base URL | - |
