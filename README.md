# 🚀 Janito: Natural Programming Language Agent

**Current Version: 1.5.x**  
See [CHANGELOG.md](./CHANGELOG.md) and [RELEASE_NOTES_1.5.md](./RELEASE_NOTES_1.5.md) for details on the latest release.

Janito is an AI-powered assistant for the command line and web that interprets natural language instructions to edit code, manage files, and analyze projects using patterns and tools designed by experienced software engineers. It prioritizes transparency, interactive clarification, and precise, reviewable changes.

---

## ⚡ Quick Start

## 🖥️ Supported Human Interfaces
Janito supports multiple ways for users to interact with the agent:

- **CLI (Command Line Interface):** Run single prompts or commands directly from your terminal (e.g., `janito "Refactor the data processing module"`).
- **CLI Chat Shell:** Start an interactive chat session in your terminal for conversational workflows (`janito`).
- **Web Interface:** Launch a browser-based UI for chat and project management (`janito --web`).

_The API is not considered a human-oriented interface and is omitted here._

### 🛠️ Common CLI Modifiers
You can alter Janito's behavior in any interface using these flags:

- `--system` / `--system-file`: Override or customize the system prompt for the session.
- `--no-tools`: Disable all tool usage (Janito will only use the language model, no file/code/shell actions).
- `--vanilla`: Disables tools, system prompt, and temperature settings for a pure LLM chat experience.

These modifiers can be combined with any interface mode for tailored workflows.


Run a one-off prompt:
```bash
janito "Refactor the data processing module to improve readability."
```

Or start the interactive chat shell:
```bash
janito
```

Launch the web UI:
```bash
janito --web
```

---

## ✨ Key Features
- 📝 **Code Editing via Natural Language:** Modify, create, or delete code files simply by describing the changes.
- 📁 **File & Directory Management:** Navigate, create, move, or remove files and folders.
- 🧠 **Context-Aware:** Understands your project structure for precise edits.
- 💬 **Interactive User Prompts:** Asks for clarification when needed.
- 🧩 **Extensible Tooling:** Built-in tools for file operations, shell commands, directory and file management, Python code execution and validation, text replacement, and more. Key tools include:
  - `find_files`: Find files in directories matching a pattern (supports recursion and result limits).
  - `get_lines`: Retrieve specific lines from files for efficient context.
  - `get_file_outline`: Get a structural outline of a file (non-empty lines).
  - `append_text_to_file`: Append text to the end of a file.
  - `replace_text_in_file`: Replace exact text fragments in files (with optional replace-all).
  - `create_file`: Create or update a file with given content.
  - `remove_file`: Remove a file from the filesystem.
  - `create_directory`: Create a new directory (with optional overwrite).
  - `remove_directory`: Remove a directory (with optional recursion).
  - `search_files`: Search for a text pattern in all files within directories and return matching lines.
  - `python_exec`: Execute arbitrary Python code and capture output.
  - `py_compile`: Validate Python files for syntax correctness using Python's built-in compiler.
  - `run_bash_command`: Execute bash commands and capture live output (with timeout and confirmation options).
  - `ask_user`: Prompt the user for input or clarification interactively.
  - `fetch_url`: Fetch the content of a web page and extract its text (with optional search strings).
- 🌐 **Web Interface (In Development):** Simple web UI for streaming responses and tool progress.

## 📦 Installation

### Requirements
- Python 3.10+

...

### Configuration & CLI Options

See [CONFIGURATION.md](./CONFIGURATION.md) for all configuration parameters, CLI flags, and advanced usage details.
| `system_file`             | Use a plain text file as the system prompt (takes precedence over `system_prompt`)         | `--system-file` (CLI only)                                     | _None_                                     |
| `temperature`             | Sampling temperature (float, e.g., 0.0 - 2.0)                                              | `--temperature` or config                                      | 0.2                                        |
| `max_tokens`              | Maximum tokens for model response                                                          | `--max-tokens` or config                                      | 200000                                     |
| `max_rounds`              | Maximum number of agent rounds per prompt/session                                          | `--max-rounds` or config                                      | 50                                         |
| `max_tools`               | Maximum number of tool calls allowed within a chat session                                 | `--max-tools` or config                                       | _None_ (unlimited)                         |
| `no_tools`           | Disable tool use (no tools passed to agent)                                                | `-n`, `--no-tools` (CLI only)                                   | False                                       |
| `trust`                   | Trust mode: suppresses run_bash_command output, only shows output file locations                  | `--trust` (CLI only)                                           | False                                       |
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


### Obtaining an API Key from OpenRouter

To use Janito with OpenRouter, you need an API key:

1. Visit https://openrouter.ai and sign up for an account.
2. After logging in, go to your account dashboard.
3. Navigate to the "API Keys" section.
4. Click "Create new key" and copy the generated API key.
5. Set your API key in Janito using:
   ```bash
   python -m janito --set-api-key YOUR_OPENROUTER_KEY
   ```
   Or add it to your configuration file as `api_key`.

**Keep your API key secure and do not share it publicly.**

### Using Azure OpenAI

For details on using models hosted on Azure OpenAI, see [AZURE_OPENAI.md](./AZURE_OPENAI.md).


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



---

## 🧩 System Prompt & Role

Janito operates using a system prompt template that defines its behavior, communication style, and capabilities. By default, Janito assumes the role of a "software engineer"—this means its responses and actions are tailored to the expectations and best practices of professional software engineering.

- **Role:** You can customize the agent's role (e.g., "data scientist", "DevOps engineer") using the `--role` flag or config. The default is `software engineer`.
- **System Prompt Template:** The system prompt is rendered from a Jinja2 template (see `janito/agent/templates/system_instructions.j2` (now located directly under the agent directory)). This template governs how the agent interprets instructions, interacts with files, and communicates with users.
- **Customization:** Advanced users can override the system prompt with the `--system` flag (raw string), or point to a custom file using `--system-file`.

The default template ensures the agent:
- Prioritizes safe, reviewable, and minimal changes
- Asks for clarification when instructions are ambiguous
- Provides concise plans before taking action
- Documents any changes made

For more details or to customize the prompt, see the template file at `janito/agent/templates/system_instructions.j2`.

---


## 🥛 Vanilla Mode

Janito supports a "vanilla mode" for pure LLM interaction:

- No tools: Disables all tool use (no file operations, shell commands, etc.).
- No system prompt: The LLM receives only your input, with no system prompt or role injected.
- No temperature set: The temperature parameter is not set (unless you explicitly provide `-t`/`--temperature`).

Activate vanilla mode with the CLI flag:

```bash
python -m janito --vanilla "Your prompt here"
```

Or in chat shell mode:

```bash
python -m janito --vanilla
```

Vanilla mode is ideal for:
- Testing raw model behavior
- Comparing LLM output with and without agent guidance
- Ensuring no agent-side intervention or context is added

> Note: Vanilla mode is a runtime switch and does not change the Agent API or class signatures. It is controlled via CLI/config only.
