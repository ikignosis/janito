# 🚀 Aurora: Natural Language Code Editing Agent

Aurora is a command-line and web-based AI agent designed to **edit code and manage files** using natural language instructions.

---

## ✨ Key Features
- 📝 **Code Editing via Natural Language:** Modify, create, or delete code files simply by describing the changes.
- 📁 **File & Directory Management:** Navigate, create, move, or remove files and folders.
- 🧠 **Context-Aware:** Understands your project structure for precise edits.
- 💬 **Interactive User Prompts:** Asks for clarification when needed.
- 🧩 **Extensible Tooling:** Built-in tools for file operations, shell commands, and more.
- 🌐 **Web Interface:** Stream responses and tool progress via a simple web UI.

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

## 💻 Usage

### Command Line Interface
Run Aurora with a single prompt:
```bash
python -m aurora "Refactor the data processing module to improve readability."
```

### Default Interactive Chat Shell
If no prompt is provided, Aurora launches an **interactive chat shell** by default.

- Supports **multiline input** (end with a single `.` on a line or Ctrl+D/Z).
- **Interrupt** agent requests with Ctrl+C.
- Pressing Enter on an empty line sends a "continue" command.
- **Session is saved automatically** after each message.
- Restore last session on startup with `--continue-session` or inside the shell with `/continue`.

#### Special Commands inside the Shell
- `/exit`: Exit chat mode.
- `/restart`: Restart the CLI.
- `/paste`: Paste multiline input.
- `/help`: Show help message.
- `/system`: Show the current system prompt.
- `/continue`: Restore the last saved conversation.
- `/reset`: Reset conversation history.
- `/clear`: Clear the terminal screen.

### Command Line Options
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

For more details, see `docs/structure.md`.
