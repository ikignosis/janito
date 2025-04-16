# Developer Guide: Creating a New Tool

This guide explains how to add a new tool (function) to the project so it can be exposed to the agent and OpenAI-compatible APIs.

## Requirements

- **Type hints**: Every parameter must have a Python type hint.
- **Docstring**: The function must have a Google-style docstring with a description for each parameter under an `Args:` section.
- **Parameter descriptions**: Every parameter must have a corresponding description in the docstring. If any are missing, an error will be raised at registration time.

## Example

```python
def my_tool(filename: str, count: int) -> None:
    """
    Processes a file a given number of times.

    Args:
        filename (str): The path to the file to process.
        count (int): How many times to process the file.
    """
    # Implementation here
```

## Steps to Add a Tool

1. **Define your function** with type hints and a Google-style docstring as shown above.
2. **Register your tool** using the `@ToolHandler.register_tool` decorator:

```python
from janito.agent.tool_handler import ToolHandler

@ToolHandler.register_tool
def my_tool(filename: str, count: int) -> None:
    """
    Processes a file a given number of times.

    Args:
        filename (str): The path to the file to process.
        count (int): How many times to process the file.
    """
    # Implementation here
```

3. **Descriptions are required** for all parameters. If a parameter is missing a description, registration will fail with an error.

## Docstring Style

- Use the **Google style** for docstrings:

```python
"""
Function summary.

Args:
    param1 (type): Description of param1.
    param2 (type): Description of param2.
"""
```

- The `Args:` section must list each parameter, its type, and a description.

## What Happens If You Omit a Description?

If you forget to document a parameter, you will see an error like:

```
ValueError: Parameter 'count' in tool 'my_tool' is missing a description in the docstring.
```

## Summary

- Always provide type hints and parameter descriptions.
- Use Google-style docstrings.
- Registration will fail if any parameter is undocumented.

Happy coding!
