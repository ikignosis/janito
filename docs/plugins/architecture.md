# Plugin Architecture

## Overview

The Janito plugin architecture is designed to provide a flexible and extensible system for adding functionality. The architecture separates the interface definitions from the actual implementations, allowing for organized plugin management while maintaining a clean codebase.

## Architecture Components

### Plugin Interface Layer

Located in the `plugins/` directory, this layer contains the plugin definitions and interfaces. Each plugin is organized by functional domain:

```
plugins/
├── core/           # Core system functionality
│   ├── filemanager/
│   ├── codeanalyzer/
│   └── system/
├── web/            # Web-related functionality
│   └── webtools/
├── dev/            # Development tools
│   ├── pythondev/
│   └── visualization/
└── ui/             # User interface
    └── userinterface/
```

### Implementation Layer

The actual tool implementations are located in `janito/tools/adapters/local/`. This separation ensures that the core functionality remains stable while the plugin interfaces can be organized and extended.

```
janito/tools/adapters/local/
├── create_file.py
├── read_files.py
├── view_file.py
├── replace_text_in_file.py
├── validate_file_syntax/
├── create_directory.py
├── remove_directory.py
├── remove_file.py
├── copy_file.py
├── move_file.py
├── find_files.py
├── get_file_outline/
├── search_text/
├── run_powershell_command.py
├── fetch_url.py
├── open_url.py
├── open_html_in_browser.py
├── python_code_run.py
├── python_command_run.py
├── python_file_run.py
├── read_chart.py
└── ask_user.py
```

## Resource Flow

1. **Plugin Registration**: Plugins are registered with the system at startup
2. **Tool Discovery**: The system discovers available tools from registered plugins
3. **Resource Contribution**: Each plugin contributes its tools to the global tool registry
4. **Tool Execution**: When a tool is called, the system routes the request to the appropriate implementation

## Plugin Loading Process

1. **Discovery**: The system scans for plugins in `./plugins/`, `~/.janito/plugins/`, and remote repositories
2. **Validation**: Plugin metadata and interfaces are validated
3. **Initialization**: The `initialize()` method is called on each loaded plugin
4. **Registration**: Tools and commands are registered with the system
5. **Availability**: Plugins are now available for use

## Resource Contribution Mechanism

Plugins contribute resources through several methods:

### Tools

The primary resource type, tools are registered via the `get_tools()` method:

```python
def get_tools(self) -> List[Type[ToolBase]]:
    return [HelloWorldTool, CalculatorTool]
```

### Commands

CLI commands are contributed through `get_commands()`:

```python
def get_commands(self) -> Dict[str, Any]:
    return {"mycommand": my_command_handler}
```

### Configuration

Plugins can define their configuration schema:

```python
def get_config_schema(self) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "timeout": {"type": "number", "default": 30}
        }
    }
```

## Security Model

The architecture includes several security features:

- **Permission System**: Each tool has defined read, write, and execute permissions
- **Path Validation**: File operations include path validation to prevent directory traversal
- **Sandboxing**: Potentially dangerous operations are sandboxed and monitored
- **User Confirmation**: Sensitive operations require explicit user approval
- **Timeouts**: Long-running operations are automatically terminated

## Extension Points

The architecture supports several extension points:

- **New Plugins**: Add new functionality by creating plugins in the `plugins/` directory
- **Custom Tools**: Implement new tools by extending `ToolBase`
- **Remote Plugins**: Load plugins from external repositories
- **Configuration**: Customize plugin behavior through configuration files

This architecture enables a powerful, secure, and extensible system for building AI-assisted development tools.