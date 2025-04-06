# Project Structure and Purpose

## Core Package: `aurora`
- `aurora/__init__.py`: Defines the package version (`__version__`).
- `aurora/__main__.py`: Main CLI entry point. Parses command line arguments, manages configuration, initializes the agent, and handles interaction. **Supports single prompt mode and interactive chat mode (`--chat`)**.
- `aurora/render_prompt.py`: Renders the system prompt template.
- `aurora/chat.py`: Implements an interactive chat loop, repeatedly asking user input and calling the agent.

## Agent Subpackage: `aurora.agent`
- `aurora/agent/__init__.py`: Marks the agent module as a package.
- `aurora/agent/agent.py`: Defines the `Agent` class, the core LLM interaction logic.
- `aurora/agent/config.py`: Configuration management classes:
  - `FileConfig`: Loads/saves JSON configs (local/global)
  - `RuntimeConfig`: In-memory, reset-on-restart config
  - `EffectiveConfig`: Merged, read-only view of all configs
  - Singleton instances: `runtime_config`, `local_config`, `global_config`, `effective_config`
- `aurora/agent/conversation.py`: Manages conversation history.
- `aurora/agent/tool_handler.py`: Handles tool execution.

### Tools (`aurora/agent/tools/`)
- `ask_user.py`: Tool to ask user questions.
- `bash_exec.py`: Run bash commands, live output.
- `create_directory.py`: Create directories.
- `create_file.py`: Create files.
- `fetch_url.py`: Fetch webpage text.
- `find_files.py`: Recursive file search respecting .gitignore.
- `gitignore_utils.py`: Helpers for .gitignore filtering.
- `move_file.py`: Move files/directories.
- `remove_file.py`: Delete files.
- `rich_live.py`, `rich_utils.py`: Terminal output formatting.
- `search_text.py`: Search text in files.
- `view_file.py`: View file contents or directory listing.
- `__init__.py`: Marks tools as a package.

## Templates
- `aurora/templates/system_instructions.j2`: Jinja2 template for system prompt.

## Web Server Package: `aurora.web`
- `aurora/web/__init__.py`: Marks the web module as a package.
- `aurora/web/__main__.py`: **Module entry point.** Allows running the web server via `python -m aurora.web [port]`. Parses optional port argument, then starts the Flask app.
- `aurora/web/app.py`: Defines the Flask app, initializes the `Agent`, provides `/`, `/execute` (standard POST), `/execute_stream` (Server-Sent Events streaming chunks tagged with command_id), and a dummy `/favicon.ico` endpoint.
- `aurora/web/templates/index.html`: Default index page served by Flask.

## Documentation
- `docs/structure.md`: This file. Explains the purpose of each file and folder.

## Summary
- CLI: `python -m aurora`
- Web: `python -m aurora.web`
- Both use the same core `Agent` class and config system.
- `/execute_stream` endpoint streams partial responses as SSE with unique command IDs.
