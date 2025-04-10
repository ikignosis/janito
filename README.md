# 🚀 Aurora: Natural Language Code Editing Agent

## ⚡ Quick Start

Run a one-off prompt:
```bash
python -m aurora "Refactor the data processing module to improve readability."
```

Or start the interactive chat shell:
```bash
python -m aurora
```

Launch the web UI:
```bash
python -m aurora.web
```

---

Aurora is a command-line and web-based AI agent designed to **edit code and manage files** using natural language instructions.

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

### Install dependencies
```bash
pip install -e .
```

### Set your API key
Aurora uses OpenAI-compatible APIs (default: `openrouter/quasar-alpha`). Set your API key as an environment variable:
```bash
export OPENROUTER_API_KEY=your_api_key_here
```

### Obtain an API key from openrouter.io
1. Visit [https://openrouter.io/](https://openrouter.io/)
2. Sign in or create a free account.
3. Navigate to **API Keys** in your account dashboard.
4. Click **Create new key**, provide a name, and save the generated key.
5. Set it as an environment variable:
```bash
export OPENROUTER_API_KEY=your_api_key_here
```

---

## ⚙️ Configuration

Aurora supports multiple ways to configure API access, model, and behavior:

### API Key

- Set via environment variable:
  ```bash
  export OPENROUTER_API_KEY=your_api_key_here
  ```
- Or save it using CLI:
  ```bash
  python -m aurora --set-api-key your_api_key_here
  ```

### Configurable Options

| Key             | Description                                               | How to set                                                      | Default                                    |
|-----------------|-----------------------------------------------------------|-----------------------------------------------------------------|--------------------------------------------|
| `api_key`       | API key for OpenAI-compatible service                     | Env var, `--set-api-key`, config file                           | _None_ (required)                          |
| `model`         | Model name to use                                         | `--set-local-config model=...` or `--set-global-config`         | `openrouter/quasar-alpha`                 |
| `base_url`      | API base URL (OpenAI-compatible endpoint)                 | `--set-local-config base_url=...` or `--set-global-config`      | `https://openrouter.ai/api/v1`            |
| `role`          | Role description for system prompt                        | CLI `--role` or config                                          | "software engineer"                     |
| `system_prompt` | Override the entire system prompt                         | CLI `--system-prompt` or config                                 | _Template-generated prompt_               |
| `max_tokens`    | Maximum tokens for model response                        | CLI `--max-tokens` or config                                    | 200000                                     |

### Config files

- **Local config:** `.aurora/config.json` (project-specific)
- **Global config:** `~/.config/aurora/config.json` (user-wide)

Set values via:

```bash
python -m aurora --set-local-config key=value
python -m aurora --set-global-config key=value
```

Show current effective config:

```bash
python -m aurora --show-config
```

---

## ☁️ Using Azure OpenAI

Aurora supports **Azure OpenAI Service** as a backend.

### How to enable

Set the environment variable:

```bash
export USE_AZURE_OPENAI=1
```

### Required environment variables

| Variable                     | Description                                                      | Example                                               |
|------------------------------|------------------------------------------------------------------|-------------------------------------------------------|
| `AZURE_OPENAI_ENDPOINT`      | Your Azure OpenAI resource endpoint                              | `https://my-resource-name.openai.azure.com`           |
| `AZURE_OPENAI_API_VERSION`   | API version (default: `2023-05-15`)                             | `2023-05-15`                                          |
| `OPENROUTER_API_KEY`         | Your Azure OpenAI API key (same as `api_key` in config)         | _Your Azure API key_                                  |

### Notes

- The **model name** you configure (via CLI or config) should be the **Azure deployment name** (not the base model name).
- All other CLI options and config settings apply as usual.
- If `USE_AZURE_OPENAI` is **not** set, Aurora defaults to OpenRouter or OpenAI-compatible APIs.

---

## 💻 Usage

### Command Line Interface
Run Aurora with a single prompt:
```bash
python -m aurora "Refactor the data processing module to improve readability."
```

### Interactive Chat Shell (Default Mode)
If no prompt is provided, Aurora launches an **interactive chat shell**.

- Supports **multiline input** (end with a single `.` on a line or Ctrl+D/Z)
- **Interrupt** agent requests anytime with Ctrl+C
- Pressing Enter on an empty line sends a "continue" command
- **Session is saved automatically** after each message
- Restore last session on startup with `--continue-session` or inside the shell with `/continue`

#### Session Management
Aurora automatically saves your conversation history and summaries. You can:
- **Continue last session**: `/continue` or `--continue-session`
- **Reset conversation**: `/reset`
- **Restart the CLI**: `/restart`
- **Exit chat**: `/exit`

#### Other Shell Commands
- `/paste`: Paste multiline input
- `/help`: Show help message
- `/system`: Show the current system prompt
- `/clear`: Clear the terminal screen

### Command Line Options
- `--web`: Launch the Aurora web server instead of the CLI interface.
- `PROMPT` (positional): Prompt to send to the model. If omitted, starts interactive chat shell.
- `-s`, `--system-prompt`: Override the system prompt.
- `-r`, `--role`: Role description for the system prompt (default: "software engineer").
- `--verbose-http`: Enable verbose HTTP logging.
- `--verbose-http-raw`: Enable raw HTTP wire-level logging.
- `--verbose-response`: Pretty print the full response object.
- `--show-system`: Show model, parameters, system prompt, and tool definitions, then exit.
- `--verbose-tools`: Print tool call parameters and results.
- `--set-local-config key=val`: Set a local config key-value pair.
- `--set-global-config key=val`: Set a global config key-value pair.
- `--show-config`: Show effective configuration and exit.
- `--version`: Show program version and exit.

---

## 🖥️ Web Interface
Launch the web server:
```bash
python -m aurora.web
```

- Access via `http://localhost:5000` (default port).
- Supports streaming LLM output and tool progress updates via Server-Sent Events.
- Terminal-style UI with Markdown rendering.
- Accepts user input and displays incremental responses.

---

## 🧰 Supported Built-in Tools
- `ask_user`: Ask the user questions.
- `bash_exec`: Run bash commands with live output.
- `create_directory`: Create directories.
- `create_file`: Create files.
- `fetch_url`: Fetch webpage text.
- `find_files`: Recursive file search respecting .gitignore.
- `move_file`: Move files/directories.
- `remove_file`: Delete files.
- `search_text`: Search text in files.
- `view_file`: View file contents or directory listing.

---

## 🤝 Contributing

We welcome contributions! To get started:

1. **Fork the repository** and clone your fork.
2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
3. **Install in editable mode with dev dependencies:**
   ```bash
   pip install -e .
   ```
4. **Style:** Follow [PEP8](https://pep8.org/) and add clear docstrings to modules, classes, and functions.
5. **Testing:** Add or update tests if applicable.
6. **Pull Requests:**
   - Describe your changes clearly.
   - Link related issues if any.
   - Keep PRs focused and minimal.

For project structure details, see `docs/structure.md`.

