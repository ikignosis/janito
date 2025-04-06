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
export OPENAI_API_KEY=your_api_key_here
```

---

## 💻 Usage

### Command Line Interface
Run Aurora in single prompt mode:
```bash
python -m aurora "Refactor the data processing module to improve readability."
```

### Command Line Options
- `PROMPT` (positional): Prompt to send to the model. If omitted, reads from stdin.
- `-s`, `--system-prompt`: Override the system prompt.
- `-r`, `--role`: Role description for the system prompt (default: "software engineer").
- `--chat`: Enter interactive chat mode.
- `--verbose-http`: Enable verbose HTTP logging.
- `--verbose-http-raw`: Enable raw HTTP wire-level logging.
- `--verbose-response`: Pretty print the full response object.
- `--show-system`: Show model, parameters, system prompt, and tool definitions, then exit.
- `--verbose-tools`: Print tool call parameters and results.
- `--set-local-config key=val`: Set a local config key-value pair.
- `--set-global-config key=val`: Set a global config key-value pair.
- `--show-config`: Show effective configuration and exit.
- `--version`: Show program version and exit.

### Interactive Chat Mode
Start an interactive conversation:
```bash
python -m aurora --chat
```
Supports multiline input (end with `.` on a line or Ctrl+D/Z).

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
