# 🏁 Janito CLI Options

This page documents all command-line options for Janito, as shown by `janito --help`. These options temporarily override configuration for a single session and do not persist changes to config files unless you use `--set` or a custom config file with `-c`.

**Syntax:** `janito [options] [prompt]`

## 💡 Overview

These options are useful for one-off runs, scripting, or experimentation. They take precedence over config files for the current invocation only.

## ⚙️ Options

| Option | Description |
|--------|-------------|
| `prompt` | Prompt to submit (optional positional argument) |
| `-h`, `--help` | Show this help message and exit |
| `-c NAME`, `--config NAME` | Use custom configuration file `~/.janito/configs/NAME.json` instead of the default config.json |
| `--verbose-api` | Print API calls and responses of LLM driver APIs for debugging/tracing. |
| `--verbose-tools` | Print info messages for tool execution in tools adapter. |
| `--verbose-agent` | Print info messages for agent event and message part handling. |
| `-z`, `--zero` | IDE zero mode: disables system prompt & all tools for raw LLM interaction |
| `-u`, `--unrestricted` | Unrestricted mode: disable path security and URL whitelist restrictions (DANGEROUS). See [Security](../security.md) for details. |
| `--multi` | Start chat mode with multiline input as default (no need for /multi command) |
| `-r`, `--read` | Enable tools that require read permissions (default: off) |
| `-w`, `--write` | Enable tools that require write permissions (default: off) |
| `-x`, `--exec` | Enable execution/run tools (allows running code or shell tools from the CLI). (default: off) |
| `--unset KEY` | Unset (remove) a config key |
| `--version` | Show program's version number and exit |
| `--list-tools` | List all registered tools |
| `--show-config` | Show the current config and config file path |
| `--list-config` | List all config files (default and custom) |
| `--list-providers` | List supported LLM providers |
| `-l`, `--list-models` | List all supported models |
| `--set-api-key API_KEY` | Set API key for the provider (requires -p PROVIDER) |
| `--set KEY=VALUE` | Set a config key |
| `-s SYSTEM_PROMPT`, `--system SYSTEM_PROMPT` | Set a system prompt |
| `-S`, `--show-system` | Show the resolved system prompt for the main agent |
| `-p PROVIDER`, `--provider PROVIDER` | Select the provider |
| `-m MODEL`, `--model MODEL` | Select the model |
| `-t TEMPERATURE`, `--temperature TEMPERATURE` | Set the temperature |
| `-v`, `--verbose` | Print extra information before answering |
| `-R`, `--raw` | Print the raw JSON response from the OpenAI API (if applicable) |
| `--effort {low, medium, high, none}` | Set the reasoning effort for models that support it (low, medium, high, none) |
| `-e`, `--event-log` | Enable event logging to the system bus |
| `--event-debug` | Print debug info on event subscribe/submit methods |

## 👨‍💻 Usage Example

```sh
janito [options] [prompt]
janito -p openai -m gpt-3.5-turbo "Your prompt here"
janito -c myproject -p openai "Prompt for my project (uses ~/.janito/configs/myproject.json)"
janito --list-tools
janito --multi  # Start chat mode with multiline input as default
janito -u -x --read --write "Run a tool with unrestricted paths (DANGEROUS)"
```

### ⚠️ Enabling Tool Permissions

By default, tools that can read, write, or execute code are **disabled** for safety. You can enable these permissions using individual flags or a convenient shortcut:

#### Individual Permission Flags
- `-r`, `--read`: Enable tools that require read permissions
- `-w`, `--write`: Enable tools that require write permissions  
- `-x`, `--exec`: Enable execution/run tools (code execution, shell commands)

#### Quick Permission Shortcut
Use `/rwx` prefix to enable all permissions at once:
```sh
janito /rwx "Create a Python script and run it"
```

#### Examples
```sh
# Enable all permissions individually
janito -r -w -x "Create and run a Python script"

# Enable only execution tools
janito -x "Run this code: print('Hello, world!')"

# Enable read and write tools
janito -r -w "Read a file and create a new one"
```

> **Warning:** Enabling execution tools allows running arbitrary code or shell commands. Only use these options if you trust your prompt and environment.

### ⚠️ Disabling Path Security

By default, all file and directory arguments to tools are restricted to the working directory (see `--workdir`). To disable this security and allow any path (including system files), use the `-u` or `--unrestricted-paths` flag:

```sh
janito -u "Do something with C:/Windows/System32/hosts"
```
> **Warning:** Disabling path security is extremely dangerous. Only use `--unrestricted-paths` if you trust your prompt, tools, and environment.

_This page is generated from the output of `janito --help`._

## 🧠 About `--effort`

The `--effort` option allows you to set the reasoning effort for models that support it. This can influence how much computational or logical effort the model applies to your prompt. The available values are:

- `low`: Minimal reasoning effort (faster, less detailed)
- `medium`: Moderate reasoning effort (default for some models)
- `high`: Maximum reasoning effort (slower, more detailed)
- `none`: Disables special reasoning effort (model default)

> **Note:** Not all models or providers support this option. If unsupported, the option may be ignored.

## 🔧 Configuration Keys

The `--set` command supports the following configuration keys:

| Key | Description | Example |
|-----|-------------|---------|
| `provider` | Set the default provider | `--set provider=openai` |
| `model` | Set the default model | `--set model=gpt-4.1` |
| `max_tokens` | Set maximum tokens | `--set max_tokens=4000` |
| `base_url` | Set custom API base URL | `--set base_url=https://api.example.com` |
| `tool_permissions` | Set tool permission level | `--set tool_permissions=rwx` |
| `disabled_tools` | Disable specific tools | `--set disabled_tools=ask_user,python_code_run` |

For more details on disabling tools, see the [Disabling Tools Guide](../guides/disabled-tools.md).
