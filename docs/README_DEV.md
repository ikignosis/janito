# Developer Guide: Creating a New Tool (Class-Based)

This guide explains how to add a new tool (functionality) to the project so it can be exposed to the agent and OpenAI-compatible APIs.

For a list of all built-in tools and their usage, see the [Tools Reference](../janito/agent/tools/README.md).
For a technical overview of the system, see the [Architecture Guide](ARCHITECTURE.md).

## Requirements

- **Class-based tools:** All tools must be implemented as classes inheriting from `ToolBase` (see `janito/agent/tool_base.py`).
- **Type hints:** All parameters to the `call` method must have Python type hints.
- **Docstrings:**
  - The tool class must have a class-level docstring summarizing its purpose and behavior. This is user-facing.
  - The `call` method must have a Google-style docstring with a description for each parameter under an `Args:` section.
- **Parameter descriptions:** Every parameter must have a corresponding description in the docstring. If any are missing, registration will fail.

## Example: Creating a Tool

```python
from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool

@register_tool
class MyTool(ToolBase):
    """
    Processes a file a given number of times.
    """

    def call(self, filename: str, count: int) -> None:
        """
        Processes the specified file repeatedly.

        Args:
            filename (str): The path to the file to process.
            count (int): How many times to process the file.
        """
        # Implementation here
```

## Steps to Add a Tool

1. **Define your tool as a class** inheriting from `ToolBase`.
2. **Add a class-level docstring** summarizing the tool's purpose (user-facing).
3. **Implement the `call` method** with type hints and a Google-style docstring, including an `Args:` section describing every parameter.
4. **Register your tool** by decorating the class with `@register_tool` from `janito.agent.tool_registry`.
5. **Document your tool**: Update `janito/agent/tools/README.md` with a short description and usage for your new tool.

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
- The class docstring is prepended to the tool's description in the OpenAI schema and is user-facing.

## What Happens If You Omit a Description?

If you forget to document a parameter, you will see an error like:

```
ValueError: Parameter 'count' in tool 'MyTool' is missing a description in the docstring.
```

## Tool Reference

See [janito/agent/tools/README.md](../janito/agent/tools/README.md) for a list of built-in tools and their usage.

## Tool Call Limits

- You can use `--max-tools` to limit the total number of tool calls allowed in a chat session. If the limit is reached, further tool calls will be prevented.

## System Prompt Precedence

- If `--system-file` is provided, the file's content is used as the system prompt (highest priority).
- Otherwise, if `--system` or the config value is set, that string is used.
- Otherwise, a default prompt is used from the template at `janito/agent/templates/system_prompt_template.j2`.

## Interactive Shell Config Commands

Within the interactive chat shell, you can use special commands:
- `/config show` — Show effective configuration (local, global, defaults)
- `/config set local key=value` — Set a local config value
- `/config set global key=value` — Set a global config value
- `/continue` — Restore the last saved conversation
- `/reset` — Reset conversation history
- `/system` — Show the current system prompt
- `/help` — Show help message

## Installing the Development Version

See [USING_DEV_VERSION.md](USING_DEV_VERSION.md) for system_prompt_template on installing and using the latest development version of this project from GitHub.

## Summary

- Always implement tools as classes inheriting from `ToolBase`.
- Provide type hints and parameter descriptions for the `call` method.
- Use Google-style docstrings for both the class and the `call` method.
- Registration will fail if any parameter is undocumented.
- Update the tools README after adding a new tool.

Happy coding!

## Vanilla Mode (Developer Note)

Vanilla mode is activated via the CLI/config (`--vanilla`). It disables all tool registration, omits the system prompt, and does not set temperature (unless explicitly provided). This is implemented as a runtime config flag (`vanilla_mode`) and does not alter the Agent or ConversationHandler API. All logic for vanilla mode is internal and backward compatible.

## Code Style, Linting, and Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) to enforce code style and linting automatically using [Black](https://black.readthedocs.io/en/stable/) (formatter) and [Ruff](https://docs.astral.sh/ruff/) (linter).

### Setup
1. Install pre-commit if you haven't already:
   ```bash
   pip install pre-commit
   ```
2. Install the hooks:
   ```bash
   pre-commit install
   ```

### Usage
- Hooks will run automatically on `git commit`.
- To manually check all files:
   ```bash
   pre-commit run --all-files
   ```
- If any issues are found, pre-commit will attempt to fix them or display errors to resolve.

### Notes
- Always run the hooks before pushing code to ensure consistent style and linting.
- See `.pre-commit-config.yaml` for configuration details.
