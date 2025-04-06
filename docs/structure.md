# Project Structure and Purpose

## Core Package: `aurora`
- `aurora/__init__.py`: Defines the package version (`__version__`).
- `aurora/__main__.py`: Main CLI entry point. Parses command line arguments, manages configuration, initializes the agent, and handles interaction. **Supports single prompt mode and interactive chat mode (`--chat`)**. **Generates the system prompt using `render_system_prompt()` and passes it to the agent.**
- `aurora/render_prompt.py`: Renders the system prompt template using Jinja2. Used by both CLI and web app to ensure consistent prompt generation.
- `aurora/chat.py`: Implements an interactive chat loop, repeatedly asking user input and calling the agent.
  - **Supports multiline user input in chat mode. User can enter multiple lines, ending input with a single `.` on a line or EOF (Ctrl+D/Ctrl+Z).**

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
- `aurora/agent/queued_tool_handler.py`: Subclass of `ToolHandler` that injects progress updates into a queue, used for streaming tool progress in the web server.

### Tools (`aurora/agent/tools/`)
- `ask_user.py`: Tool to ask user questions.
- `bash_exec.py`: Run bash commands, live output. **Supports `on_progress` callback for streaming output lines.**
- `create_directory.py`: Create directories.
- `create_file.py`: Create files.
- `fetch_url.py`: Fetch webpage text. **Supports `on_progress` callback for fetch status updates.**
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
- `aurora/web/app.py`: Defines the Flask app, initializes the `Agent` **with a generated system prompt (same as CLI)**. Provides:
  - `/`: index page.
  - `/execute`: standard POST endpoint.
  - `/execute_stream`: **streams Server-Sent Events (SSE)** including:
    - `{"type": "content", "data": ...}` for incremental LLM output.
    - `{"type": "tool_progress", "progress": ...}` for tool execution updates.

  Uses a `QueuedToolHandler` to inject tool progress events into a queue, and an `on_content` callback to enqueue content chunks. These are streamed concurrently to the client.

- `aurora/web/templates/index.html`: Default index page served by Flask. **Terminal-style UI. Sends user input as `{ "input": "..." }` to `/execute_stream`. Renders streamed `content` and `tool_progress` messages as Markdown using marked.js.**

## Documentation
- `docs/structure.md`: This file. Explains the purpose of each file and folder.

## Summary
- CLI: `python -m aurora`
- Web: `python -m aurora.web`
- Both use the same core `Agent` class, config system, and **system prompt generation logic**.
- `/execute_stream` endpoint streams incremental LLM output and tool progress updates as SSE.
