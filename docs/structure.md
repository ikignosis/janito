# Project Structure and Purpose

## Core Package: `aurora`
- `aurora/__init__.py`: Defines the package version (`__version__`).
- `aurora/__main__.py`: Minimal CLI entry point. Delegates to `aurora.cli.main.main()`.
- `aurora/render_prompt.py`: Renders the system prompt template using Jinja2.
- `aurora/chat.py`: Implements an interactive chat loop using `prompt_toolkit`. The toolbar and startup message show key combinations: press `Esc+Enter` to submit messages, `Ctrl+D` (Unix) or `Ctrl+Z` (Windows) to exit. Multiline input is default; `/paste` command is deprecated.
- `aurora/prompts/system_instructions.txt`: Alternative or plain text version of the system prompt instructions.

## CLI Package: `aurora.cli`
- `aurora/cli/__init__.py`: Marks the CLI module as a package.
- `aurora/cli/arg_parser.py`: Defines `create_parser()` to build the CLI argument parser.
- `aurora/cli/config_commands.py`: Defines `handle_config_commands(args)` to process config-related commands (`--set-*`, `--show-config`).
- `aurora/cli/logging_setup.py`: Defines `setup_verbose_logging(args)` to configure verbose HTTP and wire-level logging.
- `aurora/cli/runner.py`: Defines `run_cli(args)` containing the main CLI logic (system prompt, agent init, chat/single prompt mode).
- `aurora/cli/main.py`: Defines `main()` which orchestrates argument parsing, config commands, logging setup, and runs the CLI.

## Agent Subpackage: `aurora.agent`
- `aurora/agent/__init__.py`: Marks the agent module as a package.
- `aurora/agent/agent.py`: Defines the `Agent` class, the core LLM interaction logic.
- `aurora/agent/config.py`: Configuration management classes and `get_api_key()`.
- `aurora/agent/conversation.py`: Manages conversation history.
- `aurora/agent/tool_handler.py`: Handles tool execution.
- `aurora/agent/queued_tool_handler.py`: Tool handler subclass for streaming tool progress.

### Tools (`aurora/agent/tools/`)
- `ask_user.py`: Tool to ask user questions. Uses a `prompt_toolkit` multiline input prompt with Esc+Enter submission, matching the chat interface style.
- `bash_exec.py`: Run bash commands, live output.
- `create_directory.py`: Create directories.
- `create_file.py`: Create files.
- `fetch_url.py`: Fetch webpage text.
- `find_files.py`: Recursive file search respecting .gitignore.
- `file_str_replace.py`: Replace exact string occurrences in a file with a new string.
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
- `aurora/web/__main__.py`: Web server entry point.
- `aurora/web/app.py`: Defines the Flask app and API endpoints.
- `aurora/web/templates/index.html`: Default index page served by Flask.
- `aurora/web/static/app.js`: JavaScript for the web UI.
- `aurora/web/static/style.css`: CSS styles for the web UI.
- `aurora/web/docs/structure.md`: Duplicate or misplaced copy of the project structure documentation.

## Documentation
- `docs/structure.md`: Main documentation file explaining the purpose of each file and folder.

## Build Artifacts
- `build/`, `dist/`: Build output directories containing compiled packages and distribution archives.

## Summary
- CLI: `python -m aurora`
- Web: `python -m aurora.web`
- Both use the same core `Agent` class, config system, API key retrieval logic (`get_api_key()`), and system prompt generation.
- `/execute_stream` endpoint streams incremental LLM output and tool progress updates as SSE.
