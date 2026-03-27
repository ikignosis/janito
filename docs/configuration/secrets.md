# Secrets

janito stores sensitive configuration like API keys securely in a separate secrets file.

## Secrets File Location

Secrets are stored in `~/.janito/secrets.json`

## Setting Secrets

### Gmail Credentials

```bash
# Set Gmail username
janito --set-secret gmail_username=your-email@gmail.com

# Set Gmail app password
janito --set-secret gmail_password=your-app-password
```

### OneDrive Credentials

```bash
# Set Azure client ID
janito --set-secret azure_client_id=your-client-id
```

### Custom Secrets

```bash
janito --set-secret my_api_key=your-key
janito --set-secret another_service=token123
```

## Viewing Secrets

```bash
janito --show-secrets
```

Secrets are partially masked in the output for security.

## Clearing Secrets

Remove a specific secret:

```bash
janito --clear-secret gmail_username
```

## Security Notes

- Secrets are stored locally in `~/.janito/secrets.json`
- The file is stored with restricted permissions (600 on Unix systems)
- API keys are partially masked when displayed
- Never share your secrets file or commit it to version control

## Secrets Format

The secrets file is a simple JSON dictionary:

```json
{
    "gmail_username": "your-email@gmail.com",
    "gmail_password": "xxxx xxxx xxxx xxxx",
    "azure_client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

## Related

- [Gmail Tools](../tools/gmail.md) - Full Gmail setup guide
- [OneDrive Tools](../tools/onedrive.md) - Full OneDrive setup guide
