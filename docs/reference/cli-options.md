# CLI Options

Complete reference for janito command-line options.

## Usage

```bash
janito [options] [prompt]
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
janito --config
janito --show-config
janito --set provider=openai --set model=gpt-4
```

### Set Secrets

```bash
janito --set-secret gmail_username=user@gmail.com
janito --set-secret gmail_password=xxxx xxxx xxxx xxxx
janito --set-secret azure_client_id=xxx-xxx
janito --clear-secret gmail_password
```

### Enable Tools

```bash
janito --gmail "Show my emails"
janito --onedrive "List files"
janito --onedrive status
```

### Logging

```bash
janito --log=info "prompt"
janito --log=debug "prompt"
janito --log=info,debug "prompt"
```

## Configuration Keys

| Key | Description | Default |
|-----|-------------|---------|
| `provider` | Provider type | `openai` |
| `model` | Model name | `gpt-4` |
| `context_window` | Context window size | `65536` |
| `endpoint` | API endpoint URL | - |
| `base_url` | Base URL | - |
