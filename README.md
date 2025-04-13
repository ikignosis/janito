# 🚀 Janito: Natural Language Code Editing Agent

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

Janito is a command-line and web-based AI agent designed to **edit code and manage files** using natural language instructions.

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
- Python 3.8+

...

### Configurable Options

| Key                 | Description                                                                                 | How to set                                                      | Default                                    |
|---------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------|--------------------------------------------|
| `api_key`           | API key for OpenAI-compatible service                                                       | `--set-api-key`, config file                                    | _None_ (required)                          |
| `model`             | Model name to use                                                                           | `--set-local-config model=...` or `--set-global-config`         | `openrouter/optimus-alpha`                 |
| `base_url`          | API base URL (OpenAI-compatible endpoint)                                                   | `--set-local-config base_url=...` or `--set-global-config`      | `https://openrouter.ai/api/v1`            |
| `role`              | Role description for system prompt                                                          | CLI `--role` or config                                          | "software engineer"                     |
| `system_prompt`     | Override the entire system prompt as a raw string.                                          | CLI `--system-prompt` or config                                 | _Template-generated prompt_               |
| `system_prompt_file`| Use a plain text file as the system prompt (no template rendering, takes precedence over `system_prompt`). | CLI `--system-file` | _None_ |
| `temperature`       | Sampling temperature (float, e.g., 0.0 - 2.0)                                              | CLI `--temperature` or config                                    | 0.2                                        |
| `max_tokens`        | Maximum tokens for model response                                                          | CLI `--max-tokens` or config                                    | 200000                                     |

#### System Prompt Precedence

- If `--system-file` is provided, the file's content is used as the system prompt (no template rendering).
- Otherwise, if `--system-prompt` or the config value is set, that string is used.
- Otherwise, a default template is rendered using the current role.

...