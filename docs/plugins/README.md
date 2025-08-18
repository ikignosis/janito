# Janito Plugin System Documentation

This directory contains comprehensive documentation for the Janito plugin system, consolidated from multiple sources for easier access.

## Quick Navigation

- **[Plugin Development Guide](plugin-development.md)** - Complete guide for creating plugins
- **[Remote Plugins](remote-plugins.md)** - Using plugins from remote repositories
- **[Built-in Plugins](../built-in-plugins.md)** - Documentation for included plugins
- **[API Reference](api-reference.md)** - Technical details and interfaces
- **[Examples](examples/)** - Working plugin examples

## Overview

The Janito plugin system allows you to extend functionality with custom tools, commands, and features. Plugins can be:

- **Local plugins** - Stored in `./plugins/` or `~/.janito/plugins/`
- **Remote plugins** - Loaded from the `ikignosis/janito-plugins` repository
- **Built-in plugins** - Included with janito-coder

## Quick Start

### Creating a Basic Plugin

```python
from janito.plugins.base import Plugin, PluginMetadata
from janito.tools.tool_base import ToolBase, ToolPermissions

class HelloTool(ToolBase):
    tool_name = "hello"
    permissions = ToolPermissions(read=True, write=False, execute=True)
    
    def run(self, name="World"):
        return f"Hello, {name}!"

class HelloPlugin(Plugin):
    def get_metadata(self):
        return PluginMetadata(
            name="hello",
            version="1.0.0",
            description="A simple greeting plugin",
            author="You"
        )
    
    def get_tools(self):
        return [HelloTool]
```

### Enabling Plugins

Add to `janito.json`:

```json
{
  "plugins": {
    "load": {
      "hello": true
    }
  }
}
```

## Available Documentation

### Core Documentation
- [Plugin Development Guide](plugin-development.md) - Step-by-step plugin creation
- [Remote Plugins](remote-plugins.md) - Using community plugins
- [Configuration](configuration.md) - Plugin configuration options

### Built-in Plugins
- [Git Analyzer](../built-in-plugins/git-analyzer.md) - Git repository analysis
- [Code Navigator](../built-in-plugins/code-navigator.md) - Code navigation tools
- [Example Plugin](../built-in-plugins/example.md) - Basic plugin example

### Advanced Topics
- [Plugin Architecture](architecture.md) - System design and internals
- [Testing Plugins](testing.md) - Writing tests for plugins
- [Publishing Plugins](publishing.md) - Sharing plugins with the community

## Getting Help

- **Issues**: Report problems on GitHub
- **Discussions**: Join community forums
- **Examples**: Check the `examples/` directory for working samples

## Directory Structure

```
docs/plugins/
├── README.md                    # This file
├── plugin-development.md        # Complete development guide
├── remote-plugins.md           # Remote repository usage
├── built-in-plugins/           # Built-in plugin docs
│   ├── git-analyzer.md
│   ├── code-navigator.md
│   └── example.md
├── examples/                   # Sample plugins
│   ├── basic/
│   ├── intermediate/
│   └── advanced/
└── api-reference.md          # Technical reference
```