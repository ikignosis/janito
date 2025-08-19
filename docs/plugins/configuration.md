# Plugin Configuration

## Overview

This document explains how to configure plugins in the Janito system. Plugin configuration allows you to customize the behavior of plugins to suit your specific needs and environment.

## Configuration Methods

Plugins can be configured through the main configuration file `janito.json`. The configuration is organized under the `plugins` key:

```json
{
  "plugins": {
    "load": {
      "core.filemanager": true,
      "core.codeanalyzer": true,
      "core.imagedisplay": true,
      "web.webtools": false
    },
    "config": {
      "core.filemanager": {
        "max_file_size": 1000000,
        "backup_enabled": true
      },
      "web.webtools": {
        "timeout": 30,
        "user_agent": "Janito/1.0"
      }
    }
  }
}
```

## Configuration Options

### Plugin Loading

The `plugins.load` section controls which plugins are enabled:

```json
"plugins": {
  "load": {
    "core.filemanager": true,
    "dev.pythondev": true,
    "ui.userinterface": true,
    "core.imagedisplay": true
  }
}
```

Setting a plugin to `false` disables it completely.

### Plugin-Specific Configuration

The `plugins.config` section contains configuration options for individual plugins. Each plugin may have its own set of configurable parameters.

#### File Manager Plugin

```json
"core.filemanager": {
  "max_file_size": 1000000,
  "backup_enabled": true,
  "default_encoding": "utf-8"
}
```

#### Web Tools Plugin

```json
"web.webtools": {
  "timeout": 30,
  "user_agent": "Janito/1.0",
  "max_redirects": 5
}
```

#### Python Development Plugin

```json
"dev.pythondev": {
  "default_timeout": 60,
  "python_interpreter": "python3"
}
```

#### System Tools Plugin

```json
"core.system": {
  "command_timeout": 60,
  "require_confirmation": true
}
```

## Configuration Validation

Plugins can define a JSON schema for their configuration. The system validates configurations against these schemas to ensure correctness. If a plugin provides a schema through `get_config_schema()`, the system will validate the configuration before applying it.

## Dynamic Configuration

Plugins can be reconfigured at runtime using CLI commands:

```bash
janito --set-plugin-config "core.filemanager.max_file_size=2000000"
janito --disable-plugin "web.webtools"
janito --enable-plugin "dev.visualization"
```

## Default Configuration

If no configuration is provided, plugins use sensible defaults. The default configuration enables all built-in plugins and uses conservative settings for security and performance.

## Configuration Best Practices

- **Security First**: Configure timeouts and limits to prevent denial-of-service conditions
- **Environment Specific**: Adjust configuration based on your development environment
- **Documentation**: Document custom configurations for team sharing
- **Testing**: Test configuration changes in a safe environment before deployment

## Troubleshooting

If plugins are not behaving as expected:

1. Check the configuration syntax in `janito.json`
2. Verify that the plugin is enabled in the `plugins.load` section
3. Check for validation errors in the logs
4. Review the plugin's documentation for required configuration options

Proper configuration ensures that plugins work effectively and securely in your development workflow.