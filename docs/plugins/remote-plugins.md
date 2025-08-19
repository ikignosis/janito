# Remote Plugins

## Overview

Remote plugins allow you to load functionality from external repositories, extending Janito's capabilities without local installation. This feature enables access to community-developed tools and keeps your system up-to-date with the latest features.

## Remote Plugin Sources

By default, Janito supports loading plugins from the official repository:

- **GitHub Repository**: `https://github.com/ikignosis/janito-plugins.git`

## Configuration

To enable remote plugins, add the repository configuration to your `janito.json`:

```json
{
  "plugins": {
    "repository": {
      "url": "https://github.com/ikignosis/janito-plugins.git",
      "branch": "main",
      "auto_update": true
    }
  }
}
```

### Configuration Options

- **url**: The Git repository URL containing the plugins
- **branch**: The branch to use (default: "main")
- **auto_update**: Whether to automatically check for updates (default: true)
- **verify_ssl**: Whether to verify SSL certificates (default: true)

## Plugin Discovery

Remote plugins are discovered automatically when the system starts. The discovery process:

1. Clones or updates the remote repository
2. Scans for plugin definitions in the repository
3. Validates plugin metadata and interfaces
4. Registers available plugins

## Usage

Once configured, remote plugins can be enabled like local plugins:

```json
{
  "plugins": {
    "load": {
      "remote.example-plugin": true,
      "remote.advanced-tools": true
    }
  }
}
```

## Security

Remote plugins include several security features:

- **Source Verification**: Repository URLs are validated
- **Sandboxing**: Remote plugins run in a restricted environment
- **User Confirmation**: First-time use requires explicit approval
- **Signature Verification**: Optional GPG signature checking for plugin integrity

## Update Management

Remote plugins can be updated manually or automatically:

### Manual Update
```bash
janito --update-remote-plugins
```

### List Available Plugins
```bash
janito --list-remote-plugins
```

## Benefits

- **Easy Access**: Use community plugins without manual installation
- **Automatic Updates**: Keep plugins up-to-date with the latest features
- **Version Control**: Plugins are managed through Git for reliability
- **Community Sharing**: Share your own plugins with the community

## Limitations

- **Network Dependency**: Requires internet connection for initial setup and updates
- **Security Review**: Always review remote plugin code before use
- **Performance**: Slight delay during startup for repository synchronization

Remote plugins extend Janito's functionality while maintaining security and ease of use.