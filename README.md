# 🚀 Janito: Natural Programming Language Agent

**Current Version: 1.5.x**  
See [CHANGELOG.md](./CHANGELOG.md) and [RELEASE_NOTES_1.5.md](./RELEASE_NOTES_1.5.md) for details on the latest release.

Janito is an AI-powered assistant for the command line and web that interprets natural language instructions to edit code, manage files, and analyze projects using patterns and tools designed by experienced software engineers. It prioritizes transparency, interactive clarification, and precise, reviewable changes.

For a technical overview, see the [Architecture Guide](docs/ARCHITECTURE.md).

---

## ⚡ Quick Start

## 🖥️ Supported Human Interfaces
Janito supports multiple ways for users to interact with the agent:

- **CLI (Command Line Interface):** Run single prompts or commands directly from your terminal (e.g., `janito "Refactor the data processing module"`).
- **CLI Chat Shell:** Start an interactive chat session in your terminal for conversational workflows (`janito`).
- **Web Interface:** Launch a browser-based UI for chat and project management (`janito --web`).


![Janito Terminal Screenshot](https://github.com/joaompinto/janito/blob/main/docs/imgs/terminal.png?raw=true)

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

While in the chat shell, you can use special commands like `/reload` to reload the system prompt from a file without restarting your session. See the documentation for more shell commands.

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
- 🧩 **Extensible Tooling:** Built-in tools for file operations, shell commands, directory and file management, Python code execution and validation, text replacement, and more.
  - See [janito/agent/tools/README.md](janito/agent/tools/README.md) for the full list of built-in tools and their usage details. For the message handler model, see [docs/MESSAGE_HANDLER_MODEL.md](docs/MESSAGE_HANDLER_MODEL.md).
- 🌐 **Web Interface (In Development):** Simple web UI for streaming responses and tool progress.

## 📦 Installation

### Requirements
- Python 3.10+


### Contributing & Developer Guide

If you want to extend Janito or add new tools, see the [Developer Guide](docs/README_DEV.md) for instructions, tool registration requirements, and code style guidelines. For the full list of built-in tools and their usage, see the [Tools Reference](janito/agent/tools/README.md).



For the full changelog, see [CHANGELOG.md](./CHANGELOG.md).

...

### Configuration & CLI Options

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all configuration parameters, CLI flags, and advanced usage details. All CLI and configuration options have been moved there for clarity and maintainability.


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

For details on using models hosted on Azure OpenAI, see [docs/AZURE_OPENAI.md](docs/AZURE_OPENAI.md).



---

## 🧩 System Prompt & Role

Janito operates using a system prompt template that defines its behavior, communication style, and capabilities. By default, Janito assumes the role of a "software engineer"—this means its responses and actions are tailored to the expectations and best practices of professional software engineering.

- **Role:** You can customize the agent's role (e.g., "data scientist", "DevOps engineer") using the `--role` flag or config. The default is `software engineer`.
- **System Prompt Template:** The system prompt is rendered from a Jinja2 template (see `janito/agent/templates/system_instructions.j2`). This template governs how the agent interprets instructions, interacts with files, and communicates with users.
- **Customization & Precedence:** Advanced users can override the system prompt with the `--system` flag (raw string), or point to a custom file using `--system-file`. The precedence is: `--system-file` > `--system`/config > default template.

The default template ensures the agent:
- Prioritizes safe, reviewable, and minimal changes
- Asks for clarification when instructions are ambiguous
- Provides concise plans before taking action
- Documents any changes made

For more details or to customize the prompt, see the template file at `janito/agent/templates/system_instructions.j2` and the architecture overview in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
