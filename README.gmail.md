# Gmail Tools

Gmail tools are no longer built into janito. They moved to the
**janito-gmail-plugin** plugin.

## Install & Use

```bash
# Configure the required secrets (checked by the plugin's on_start)
janito --set-secret gmail_username=your-email@gmail.com
janito --set-secret gmail_password=your-app-password

# Load the plugin (one of)
janito --plugin ../plugins/janito-gmail-plugin

# Or install it so it autoloads on every run:
janito --install-plugin https://github.com/joaompinto/janito-gmail-plugin
```

## Documentation

The full setup guide (app passwords, IMAP, tool reference, IMAP search
examples, troubleshooting, security notes) lives in the plugin's
[README.md](../plugins/janito-gmail-plugin/README.md).
