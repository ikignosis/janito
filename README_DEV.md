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

## Tool Reference

### Built-in Tools

- `find_files`: Search for files matching a pattern in directories.
- `get_lines`: Retrieve specific lines from files for efficient context.
- `py_compile_file`: Validate Python files for syntax correctness.
- `replace_text_in_file`: Replace exact text fragments in files.
- `search_files`: Search for text patterns across files.
- `python_exec`: Execute Python code and capture output.
- And more, see `janito/agent/tools/` for the full list.

### Directory Listing Tool

- Use the `list_directory` tool to list the contents of a directory up to a specified depth. Returns name, type (file/dir), last modified time, and path for each entry.

### Python File Validation Tool

- Use the `py_compile_file` tool to validate a Python file by compiling it with Python's built-in `py_compile` module. This tool is recommended for checking Python files after making changes, ensuring syntax correctness before running or deploying code.
- **Usage:**
  - Provide the path to the Python file you want to validate.
  - Optionally, set `doraise` to `True` (default) to raise exceptions on errors.
  - Returns a success message if the file is valid, or error details if compilation fails.

## Tool Call Limits

- You can use `--max-tools` to limit the total number of tool calls allowed in a chat session. If the limit is reached, further tool calls will be prevented.

## System Prompt Precedence

- If `--system-file` is provided, the file's content is used as the system prompt.
- Otherwise, if `--system-prompt` or the config value is set, that string is used.
- Otherwise, a default prompt is used.

## Interactive Shell Config Commands

Within the interactive chat shell, you can use special commands:
- `/config show` — Show effective configuration (local, global, defaults)
- `/config set local key=value` — Set a local config value
- `/config set global key=value` — Set a global config value
- `/continue` — Restore the last saved conversation
- `/reset` — Reset conversation history
- `/system` — Show the current system prompt
- `/help` — Show help message

## Summary

- Always provide type hints and parameter descriptions.
- Use Google-style docstrings.
- Registration will fail if any parameter is undocumented.

Happy coding!
