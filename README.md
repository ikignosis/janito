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

### Install dependencies
```bash
pip install -e .
```

### Set your API key
Janito uses OpenAI-compatible APIs (default: `openrouter/optimus-alpha`). Set your API key using the CLI:
```bash
python -m janito --set-api-key your_api_key_here
```

### Obtain an API key from openrouter.io
1. Visit [https://openrouter.io/](https://openrouter.io/)
2. Sign in or create a free account.
3. Navigate to **API Keys** in your account dashboard.
4. Click **Create new key**, provide a name, and save the generated key.
5. Save it using the CLI:
```bash
python -m janito --set-api-key your_api_key_here
```

---

## ⚙️ Configuration

Janito supports multiple ways to configure API access, model, and behavior:

### API Key

- Set via CLI:
  ```bash
  python -m janito --set-api-key your_api_key_here
  ```

### Configurable Options

| Key             | Description                                               | How to set                                                      | Default                                    |
|-----------------|-----------------------------------------------------------|-----------------------------------------------------------------|--------------------------------------------|
| `api_key`       | API key for OpenAI-compatible service                     | `--set-api-key`, config file                                    | _None_ (required)                          |
| `model`         | Model name to use                                         | `--set-local-config model=...` or `--set-global-config`         | `openrouter/optimus-alpha`                 |
| `base_url`      | API base URL (OpenAI-compatible endpoint)                 | `--set-local-config base_url=...` or `--set-global-config`      | `https://openrouter.ai/api/v1`            |
| `role`          | Role description for system prompt                        | CLI `--role` or config                                          | "software engineer"                     |
| `system_prompt` | Override the entire system prompt as a raw string. No file support. | CLI `--system-prompt` or config                                 | _Template-generated prompt_               |
| `temperature`   | Sampling temperature (float, e.g., 0.0 - 2.0)            | CLI `--temperature` or config                                    | 0.2                                        |
| `max_tokens`    | Maximum tokens for model response                        | CLI `--max-tokens` or config                                    | 200000                                     |



### Config files

- **Local config:** `.janito/config.json` (project-specific)
- **Global config:** `~/.config/janito/config.json` (user-wide)

Set values via:

```bash
python -m janito --set-local-config key=value
python -m janito --set-global-config key=value
```

---

## 🚀 Build and Release

Janito provides scripts for automated build and release to PyPI:

### Bash (Linux/macOS)

```bash
./tools/release.sh
```

### PowerShell (Windows)

```powershell
./tools/release.ps1
```

These scripts will:
- Check for required tools (`hatch`, `twine`)
- Validate the version in `pyproject.toml` against PyPI and git tags
- Build the package
- Upload to PyPI

---
