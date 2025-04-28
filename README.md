# 🚀 Janito: Natural Language Coding Agent

**Current Version: 1.8.1**  
See [CHANGELOG.md](./CHANGELOG.md) for details on the latest release.

Janito is an AI-powered assistant for the command line and web that interprets natural language system_prompt_template to edit code, manage files, and analyze projects using patterns and tools designed by experienced software engineers. It prioritizes transparency, interactive clarification, and precise, reviewable changes.

For a technical overview, see the [Architecture Guide](docs/reference/architecture.md).

## 🧪 Experimental Feature: termweb File Viewer

Janito now includes an experimental lightweight web file viewer for use with the CLI chat shell. This feature allows you to click on file paths in the terminal (when using a Rich-compatible terminal) and instantly preview file contents in your browser—no full IDE required!

### How to Use

- Start the CLI chat shell with the `--termweb` flag:
  ```bash
  janito --termweb
  ```
- To disable the termweb file viewer, use the `--no-termweb` flag.
- By default, the viewer runs at http://localhost:8088 (or the next available port up to 8100).
- To specify a port, use `--termweb-port 8090`.
- File paths in CLI output become clickable links that open the file in your browser.

**Note:** This feature is experimental. It is intended for quick file previews and review, not for editing or production use. Feedback is welcome!

### Why is this useful?
- Enables instant file previews from the CLI without a full IDE.
- Works with all Janito file tools and outputs that display file paths.
- Uses the Rich library’s link markup for clickable terminal links.

---

## 📖 Full Documentation & Overview
- For structured and in-depth guides, visit the [Janito Documentation Site](https://docs.janito.dev).
- For a high-level, user-friendly overview, see [janito.dev](https://janito.dev).

---

## Listing Available Tools

To list all registered tools on the command line, use the option:

```sh
janito --list-tools
```

This will display a colorful table with the name, description, and parameters of each available tool.

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
- `--trust-tools`/`-T`: Trusted tools mode (suppresses all tool output, only shows output file locations).
- `--vanilla`: Disables tools, system prompt, and temperature settings for a pure LLM chat experience.
- `--no-termweb`: Disables the termweb file viewer for terminal links.

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
- 🛠️ **Extensible Tooling:** Built-in tools for file operations, shell commands, directory and file management, Python code execution and validation, text replacement, and more.
  - See [janito/agent/tools/README.md](janito/agent/tools/README.md) for the full list of built-in tools and their usage details. For the message handler model, see [docs/MESSAGE_HANDLER_MODEL.md](docs/MESSAGE_HANDLER_MODEL.md).
- 🌐 **Web Interface (In Development):** Simple web UI for streaming responses and tool progress.

## 📦 Installation

### Requirements
- Python 3.10+


### Contributing & Developer Guide

If you want to extend Janito or add new tools, see the [Developer Guide](docs/README_DEV.md) for system_prompt_template, tool registration requirements, and code profile guidelines. For the full list of built-in tools and their usage, see the [Tools Reference](janito/agent/tools/README.md).



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

## 🧑‍💻 System Prompt & Role

Janito operates using a system prompt template that defines its behavior, communication profile, and capabilities. By default, Janito assumes the role of a "software engineer"—this means its responses and actions are tailored to the expectations and best practices of professional software engineering.

- **Role:** You can customize the agent's role (e.g., "data scientist", "DevOps engineer") using the `--role` flag or config. The default is `software engineer`.
- **System Prompt Template:** The system prompt is rendered from a Jinja2 template (see `janito/agent/templates/prompt_prompt_template.j2`). This template governs how the agent interprets system_prompt_template, interacts with files, and communicates with users.
- **Customization & Precedence:** Advanced users can override the system prompt with the `--system` flag (raw string), or point to a custom file using `--system-file`. The precedence is: `--system-file` > `--system`/config > default template.

The default template ensures the agent:
- Prioritizes safe, reviewable, and minimal changes
- Asks for clarification when system_prompt_template are ambiguous
- Provides concise plans before taking action
- Documents any changes made

For more details or to customize the prompt, see the template file at `janito/agent/templates/prompt_prompt_template.j2` and the architecture overview in [docs/reference/architecture.md](docs/reference/architecture.md).

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

## 👨‍💻 AgentProfileManager: Profile, Role, and Prompt Management

Janito now uses a dedicated `AgentProfileManager` class to manage user profiles, roles, interaction profiles, and system prompt selection. This manager:
- Stores the current role (e.g., "software engineer") and interaction profile (e.g., "default", "technical").
- Renders the system prompt from the appropriate template based on interaction profile.
- Instantiates and manages the low-level LLM Agent, passing the correct prompt.
- Provides methods to update the role, interaction profile, and refresh the prompt at runtime.

### Multiple System Prompt Templates
- The system prompt template is now selected based on the interaction profile (e.g., `default` or `technical`).
- Templates are located in `janito/agent/templates/` (see `system_prompt_template.j2` and `system_prompt_template_technical.j2`).
- You can switch interaction profiles at runtime using the profile manager, enabling different agent behaviors for different user needs.

This separation ensures that the LLM Agent remains focused on language model interaction and tool execution, while all profile, role, and prompt logic is managed at a higher level.

See `janito/agent/profile_manager.py` for implementation details.

### Agent Interaction Style

You can control the agent's behavior and prompt profile globally or per-project using the `profile` config key. See [Prompt Profiles Guide](docs/guides/prompt_profiles.md) for all available styles and combinations.
- `default`: Concise, general-purpose agent (default)
- `technical`: Strict, workflow-oriented for technical/developer use

Set globally:
```bash
janito --set-global-config profile=technical
```
Or per-project (in your project root):
```bash
janito --set-local-config profile=technical
```

You can also override for a session with the CLI flag:
```bash
janito --profile technical
```

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full details.

## 🧑‍💻 Combinatorial Style System

Janito now supports combinatorial profiles for system prompts, allowing you to combine a main profile (such as `default` or `technical`) with one or more feature extensions (such as `commit_all`).

- **Main profile:** The base agent behavior and workflow (e.g., `default`, `technical`).
- **Feature extensions:** Optional features that override or extend the main profile (e.g., `commit_all`).
- **Syntax:** Use a hyphen to combine, e.g., `technical-commit_all`.

**How it works:**
- The main profile template is loaded first.
- Each feature extension template is layered on top, overriding or extending specific blocks in the main template.
- Feature templates must use `{% extends parent_template %}` for dynamic inheritance.

**Example usage:**
```bash
janito --profile technical-commit_all
```

This will apply the `technical` profile with the `commit_all` feature enabled in the agent's system prompt.

See `janito/render_prompt.py` and `janito/agent/templates/` for implementation details and to create your own feature extensions.

---
_generated by janito.dev_
