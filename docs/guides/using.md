# Using Janito: Quickstart & Basic Usage

This guide explains how to start using Janito after installation. For an overview, see the [Introduction](../index.md). For setup, see the [Installation Guide](installation.md) and [Configuration Guide](configuration.md).

## Quickstart

After installing Janito, you can use it from the command line:

### Run a One-Off Prompt
```bash
janito "Refactor the data processing module to improve readability."
```

### Start the Interactive Chat Shell
```bash
janito
```

## Basic Usage Tips

- Use natural language to describe what you want Janito to do (e.g., "Add type hints to all functions in utils.py").
- In the chat shell, use `/help` for available commands. Use `/exec on` to enable code/shell execution tools at runtime.
- Use CLI flags to customize behavior (see [CLI Options](../reference/cli-options.md)).
- Shell commands can be executed using the built-in `run_bash_command` and `run_powershell_command` tools (when enabled).

## More Resources

- [How Janito Uses Tools](using_tools.md): Automatic tool selection details.
- Supported Models: See documentation navigation for LLM compatibility.
- [Costs & Value Transparency](../about/costs.md): Pricing and efficiency details.
