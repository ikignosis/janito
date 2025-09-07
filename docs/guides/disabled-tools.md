# Disabling Tools Guide

Janito allows you to disable specific tools to customize your workflow or enhance security. This guide explains how to disable and manage tools using configuration settings.

## Overview

By default, all tools are enabled based on their permission requirements (read, write, execute). However, you can selectively disable individual tools using the `disabled_tools` configuration setting.

## Setting Disabled Tools

### Via CLI

Use the `--set` command to disable tools:

```bash
# Disable a single tool
janito --set disabled_tools=ask_user

# Disable multiple tools (comma-separated)
janito --set disabled_tools="ask_user,python_code_run"

# Clear all disabled tools
janito --set disabled_tools=""
```

### Via Configuration File

Edit your configuration file (by default `~/.janito/config.json`, or a custom file if using `-c NAME` such as `~/.janito/configs/NAME.json`) and add the `disabled_tools` key:

```json
{
  "disabled_tools": "ask_user,python_code_run",
  "provider": "openai",
  "model": "gpt-4.1"
}
```

If you use `-c NAME`, the disabled tools will be saved and loaded from that custom config file.

## Viewing Disabled Tools

Check which tools are currently disabled:

```bash
janito --show-config
```

This will display the config file path and a section showing your disabled tools, for example:
```
Config file: /home/youruser/.janito/config.json
Disabled tools: ask_user, python_code_run
```

## Listing Available Tools

To see which tools are currently available (excluding disabled ones):

```bash
janito --list-tools
```

Disabled tools will not appear in the tool listing.

## Common Use Cases

### Security Enhancement
Disable potentially dangerous tools in production environments:
```bash
janito --set disabled_tools="python_code_run,run_powershell_command,run_bash_command"
```

### Workflow Customization
Disable tools you don't use to reduce clutter:
```bash
janito --set disabled_tools="open_url,open_html_in_browser"
```

### Session-Based Disabling
Disable tools for specific sessions:
```bash
janito --set disabled_tools=ask_user "Generate code without user interaction"
```

## Tool Names

Use the exact tool names as shown in `janito --list-tools`. Common tool names include:

- `ask_user` - Interactive user prompts
- `python_code_run` - Execute Python code
- `run_powershell_command` - Execute PowerShell commands
- `run_bash_command` - Execute bash commands
- `create_file` - Create new files
- `remove_file` - Delete files
- `open_url` - Open URLs in browser
- And many more...

## Best Practices

1. **Test Before Disabling**: Always test your workflow after disabling tools to ensure essential functionality isn't broken.

2. **Document Changes**: Keep track of which tools you've disabled and why.

3. **Use Sparingly**: Only disable tools that pose security risks or aren't needed for your specific use case.

4. **Review Regularly**: Periodically review your disabled tools list to ensure it still meets your needs.

## Troubleshooting

### Tool Still Appears Available

- Ensure you're using the exact tool name (case-sensitive)
- Check that the configuration was saved: `janito --show-config`
- Restart your terminal session if needed

### Accidentally Disabled Essential Tools

- Clear all disabled tools: `janito --set disabled_tools=""`
- Or selectively re-enable by removing from the comma-separated list

### Configuration Not Persisting

- Verify the config file path: `janito --show-config` shows the config file location at the top (if using `-c NAME`, it will show the custom config file)
- Check file permissions for your config file
- Ensure no syntax errors in the JSON configuration