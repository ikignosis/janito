# Agent and Tools Workflow and Lifecycle

This document explains how tools are integrated into Janito's agent system, covering their workflow from registration to execution and the overall lifecycle.

## Overview

Janito's agent system uses a modular approach to tool management, allowing for flexible registration, permission control, and execution of various tools. Tools are implemented as classes that inherit from `ToolBase` and are registered with a tools adapter.

## Tool Registration

### 1. Tool Implementation

Tools are implemented as classes that inherit from `ToolBase`:

- Must define a `permissions` attribute of type `ToolPermissions`
- Must implement a `run` method with proper type hints and docstrings
- Should have a unique `tool_name` class attribute

Example:
```python
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.plugins.adapters.local.adapter import register_local_tool

@register_local_tool
class MyTool(ToolBase):
    """
    Processes a file a given number of times.
    """
    permissions = ToolPermissions(read=True, write=True)
    tool_name = "my_tool"

    def run(self, filename: str, count: int) -> str:
        """
        Processes the specified file repeatedly.

        Args:
            filename (str): The path to the file to process.
            count (int): How many times to process the file.

        Returns:
            str: Status message after processing.
        """
        # Implementation here
        return f"Processed {filename} {count} times"
```

### 2. Tool Registration

Tools can be registered in two ways:

1. Using the `@register_local_tool` decorator
2. Manually registering with a `LocalToolsAdapter` instance

The decorator approach automatically registers the tool with the singleton adapter.

## Tool Permissions

Each tool defines its required permissions using the `ToolPermissions` named tuple:

- `read`: Permission to read files
- `write`: Permission to write/modify files
- `execute`: Permission to execute commands

These permissions are checked against the global allowed permissions at runtime.

## Tool Execution Lifecycle

### 1. Tool Discovery

When the agent needs to execute a tool, it first looks up the tool by name using the tools adapter.

### 2. Permission Validation

The adapter checks if the tool's required permissions are allowed by the current permission settings.

### 3. Argument Validation

Before execution, the tool's arguments are validated against both the function signature and any defined schema.

### 4. Path Security Check

For tools that work with file paths, path security validation ensures that only allowed paths are accessed.

### 5. Execution

The tool is executed with the provided arguments, and the result is returned.

### 6. Event Publishing

Throughout the execution process, various events are published to the event bus:

- `ToolCallStarted`: When a tool execution begins
- `ToolCallFinished`: When a tool execution completes successfully
- `ToolCallError`: When a tool execution encounters an error

## Error Handling

The tools adapter includes comprehensive error handling:

- Missing or invalid arguments are caught and reported
- Path security violations are detected and prevented
- Loop protection prevents infinite execution loops
- Runtime errors in tools are caught and converted to `ToolCallException`

## Customization

The tools system can be customized by:

1. Implementing custom tools adapters for different execution environments
2. Modifying permission settings at runtime
3. Disabling specific tools through configuration
4. Extending the base `ToolBase` class for specialized functionality

## Conclusion

Janito's agent and tools system provides a robust, secure, and extensible framework for integrating various functionalities. By following the established patterns for tool implementation and registration, developers can easily add new capabilities while maintaining security and consistency.