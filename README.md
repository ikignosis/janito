# 🚀 Janito: A Natural Programming Language Tool

## ⚡ Quick Start

Run a one-off prompt:
```bash
python -m janito "Refactor the data processing module to improve readability."
```

Or start the interactive chat shell:
```bash
python -m janito
```

Launch the web UI:
```bash
python -m janito.web
```

---

Janito is a command-line and web-based tool designed to **edit code and manage files** using natural language instructions.

---

## ✨ Key Features
- 📝 **Code Editing via Natural Language:** Modify, create, or delete code files simply by describing the changes.
- 📁 **File & Directory Management:** Navigate, create, move, or remove files and folders.
- 🧠 **Context-Aware:** Understands your project structure for precise edits.
- 💬 **Interactive User Prompts:** Asks for clarification when needed.
- 🧩 **Extensible Tooling:** Built-in tools for file operations, shell commands, and more.
- 🌐 **Web Interface (In Development):** Upcoming simple web UI for streaming responses and tool progress.

---

## 📦 Installation

### Requirements
- Python 3.11+

...

### Configuration & CLI Options

Below are the supported configuration parameters and CLI flags. Some options can be set via config files, CLI flags, or both. Use `python -m janito --help` for a full list, or `python -m janito --help-config` to see all config keys and their descriptions.

| Key / Flag                | Description                                                                                 | How to set                                                      | Default                                    |
|---------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------|--------------------------------------------|
| `api_key`                 | API key for OpenAI-compatible service                                                       | `--set-api-key`, config file                                    | _None_ (required)                          |
| `model`                   | Model name to use for this session                                                          | `--model` (session only), `--set-local-config model=...`, or `--set-global-config` | `openai/gpt-4.1`                 |
| `base_url`                | API base URL (OpenAI-compatible endpoint)                                                   | `--set-local-config base_url=...` or `--set-global-config`      | `https://openrouter.ai/api/v1`            |
| `role`                    | Role description for the system prompt                                                      | `--role` or config                                            | "software engineer"                     |
| `system_prompt`           | Override the entire system prompt as a raw string                                           | `--system-prompt` or config                                   | _Default prompt_               |
| `system_file`             | Use a plain text file as the system prompt (takes precedence over `system_prompt`)         | `--system-file` (CLI only)                                     | _None_                                     |
| `temperature`             | Sampling temperature (float, e.g., 0.0 - 2.0)                                              | `--temperature` or config                                      | 0.2                                        |
| `max_tokens`              | Maximum tokens for model response                                                          | `--max-tokens` or config                                      | 200000                                     |
| `max_rounds`              | Maximum number of agent rounds per prompt/session                                          | `--max-rounds` or config                                      | 50                                         |
| `max_tools`               | Maximum number of tool calls allowed within a chat session                                 | `--max-tools` or config                                       | _None_ (unlimited)                         |
| `disable_tools`           | Disable tool use (no tools passed to agent)                                                | `--disable-tools` (CLI only)                                   | False                                       |
| `template` / `template.*` | Template context dictionary for prompt rendering (nested or flat keys)                     | Config only                                                    | _None_                                     |

Other config-related CLI flags:

- `--set-local-config key=val`   Set a local config value
- `--set-global-config key=val`  Set a global config value
- `--run-config key=val`         Set a runtime (in-memory only) config value (can be repeated)
- `--show-config`                Show effective configuration and exit
- `--config-reset-local`         Remove the local config file
- `--config-reset-global`        Remove the global config file
- `--set-api-key KEY`            Set and save the API key globally
- `--help-config`                Show all configuration options and exit

Session & shell options:

- `--continue-session`           Continue from the last saved conversation
- `--web`                        Launch the Janito web server instead of CLI

Verbose/debugging flags:

- `--verbose-http`               Enable verbose HTTP logging
- `--verbose-http-raw`           Enable raw HTTP wire-level logging
- `--verbose-response`           Pretty print the full response object
- `--verbose-tools`              Print tool call parameters and results
- `--show-system`                Show model, parameters, system prompt, and tool definitions, then exit
- `--version`                    Show program's version number and exit


#### Tool Call Limits

- You can use `--max-tools` to limit the total number of tool calls allowed in a chat session. If the limit is reached, further tool calls will be prevented.

#### System Prompt Precedence

- If `--system-file` is provided, the file's content is used as the system prompt.
- Otherwise, if `--system-prompt` or the config value is set, that string is used.
- Otherwise, a default prompt is used.

#### Interactive Shell Config Commands

Within the interactive chat shell, you can use special commands:
- `/config show` — Show effective configuration (local, global, defaults)
- `/config set local key=value` — Set a local config value
- `/config set global key=value` — Set a global config value
- `/continue` — Restore the last saved conversation
- `/reset` — Reset conversation history
- `/system` — Show the current system prompt
- `/help` — Show help message

...