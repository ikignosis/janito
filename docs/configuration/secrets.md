# Secrets

janito stores sensitive configuration like API keys and credentials in a separate secrets file.

## Secrets File Location

Secrets are stored in `~/.janito/secrets.json`.

> **Note:** Provider API keys set with `--set-api-key` are stored separately in `~/.janito/auth.json`. The secrets file is for arbitrary credentials such as app passwords or Azure client IDs.

> **Note:** With `-l`/`--local`, secrets are stored in `./.janito/secrets.json`
> (the current working directory) instead of `~/.janito/secrets.json`. Reads
> resolve local values first and fall back to the global file, and
> `--list-secrets` shows both.

## Setting Secrets

### Brave Search Credentials

The `WebSearch` tool searches the web via the [Brave Search API](https://brave.com/search/api/)
and is only loaded when this secret is set:

```bash
# Set your Brave Search subscription token
janito --set-secret brave_api_key=your-brave-subscription-token
```

### Custom Secrets

```bash
janito --set-secret my_api_key=your-key
janito --set-secret another_service=token123
```

You can set multiple secrets in one command:

```bash
janito --set-secret my_api_key=your-key another_service=token123
```

## Listing Secrets

List the names of all configured secrets (values are not shown):

```bash
janito --list-secrets
```

## Retrieving a Secret

Print the value of a specific secret:

```bash
janito --get-secret my_api_key
```

## Deleting Secrets

Remove a specific secret:

```bash
janito --delete-secret my_api_key
```

## Security Notes

- Secrets are stored locally in `~/.janito/secrets.json`
- The file is stored with restricted permissions (600 on Unix systems)
- `--list-secrets` shows only key names, never values
- Never share your secrets file or commit it to version control

## Secrets Format

The secrets file is a simple JSON dictionary:

```json
{
    "my_api_key": "your-key",
    "another_service": "token123",
    "azure_client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## Related

- [Web Tools](../tools/web-search.md) - Full WebSearch / GetUrl guide
- [Plugins](../PLUGINS.md) - The janito plugin system
