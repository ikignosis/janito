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

Or, to enable clickable file links in your browser during the session:
```bash
janito --web
```

## Basic Usage Tips
- Use natural language to describe what you want Janito to do (e.g., "Add type hints to all functions in utils.py").
- In the chat shell, use `/help` for available commands. Use `/exec on` to enable code/shell execution tools at runtime.
- **Press Enter** at any time to cancel a long-running request in chat mode
- Use CLI flags to customize behavior (see [CLI Options](../reference/cli-options.md)).

## More Resources

- [How Janito Uses Tools](using_tools.md): Automatic tool selection details.
- Supported Models: See documentation navigation for LLM compatibility.
- [Costs & Value Transparency](../about/costs.md): Pricing and efficiency details.
