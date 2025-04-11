# Project Structure and Purpose

## Core Package: `janito`
- `janito/__init__.py`: Defines the package version (`__version__`).
- `janito/__main__.py`: Minimal CLI entry point. Delegates to `janito.cli.main.main()`.
- `janito/render_prompt.py`: Renders the system prompt template using Jinja2.
- `janito/prompts/system_instructions.txt`: Alternative or plain text version of the system prompt instructions.

## CLI Chat Shell Package: `janito.cli_chat_shell`
- `janito/cli_chat_shell/__init__.py`: Marks the CLI chat shell module as a package.
- `janito/cli_chat_shell/chat_loop.py`: Implements the interactive chat shell using `prompt_toolkit`. Handles multiline input, chat history, and displays a colored status toolbar. Delegates special commands to `commands.py`.
  - **Empty input behavior:** If the user presses Enter without typing anything, the shell interprets this as a request to continue and automatically sends the command `"do it"` to the agent.
  - **Interrupt handling:** Pressing Ctrl-C during an agent request will interrupt the request and return to the prompt with a message, instead of exiting the shell.
  - **Note:** The chat shell no longer displays the last saved conversation summary on startup by default. To restore a previous session, use the `--continue-session` flag or `/continue` command inside the shell.
- `janito/cli_chat_shell/commands.py`: Handles special chat shell commands:
  - `/exit`: Exit chat mode.
  - `/restart`: Restart the CLI.
  - `/help`: Show help message.
  - `/system`: Show the current system prompt.
  - `/continue`: Restore the last saved conversation and CLI prompts from `.janito/last_conversation.json`.
  - `/reset`: Reset conversation history (clears in-memory state and deletes saved conversation).

## Session Persistence
- The CLI shell automatically saves the conversation history and CLI prompts after each message or command to `.janito/last_conversation.json`.
- To continue from the last saved session:
  - Use the CLI flag `--continue-session` when starting the shell.
  - Or, inside the shell, type `/continue`.
- If neither is used, the shell starts fresh.

### Saved File
- `.janito/last_conversation.json`: Stores the last chat session, including:
  - `messages`: List of agent/user messages.
  - `prompts`: List of CLI prompt inputs.


## CLI Package: `janito.cli`
- `janito/cli/__init__.py`: Marks the CLI module as a package.
- `janito/cli/arg_parser.py`: Defines `create_parser()` to build the CLI argument parser. The positional `prompt` argument is optional; if omitted, the CLI defaults to interactive chat mode.
  - Supports `--set-api-key` to save the API key locally (stored in `.janito/config.json`).
  - Also supports `--set-local-config key=val`, `--set-global-config key=val`, and `--show-config`.
- `janito/cli/config_commands.py`: Defines `handle_config_commands(args)` to process config-related commands (`--set-*`, `--show-config`).
- `janito/cli/logging_setup.py`: Defines `setup_verbose_logging(args)` to configure verbose HTTP and wire-level logging.
- `janito/cli/runner.py`: Defines `run_cli(args)` containing the main CLI logic. If a prompt is provided, it sends a single prompt to the agent. If no prompt is provided, it enters interactive chat mode by default.
  - Loads model, API base URL, and other settings from the *unified config* (`unified_config.get(...)`), which first checks runtime/session overrides, then falls back to effective (local/global) config.
- `janito/cli/main.py`: Defines `main()` which orchestrates argument parsing, config commands, logging setup, and runs the CLI.

## Agent Subpackage: `janito.agent`
- `janito/agent/__init__.py`: Marks the agent module as a package.
- `janito/agent/agent.py`: Defines the `Agent` class, the core LLM interaction logic.
  - The `Agent` constructor accepts optional `model` and `base_url` parameters (defaulting to `'openrouter/optimus-alpha'` and `'https://openrouter.ai/api/v1'` respectively). This enables flexible use of different OpenAI-compatible endpoints and models, configurable via CLI or config files.
  - The `Agent.chat()` method returns a dictionary with:
    - `"content"`: the assistant's message text.
    - `"usage"`: a dictionary with token usage info (`prompt_tokens`, `completion_tokens`, `total_tokens`), or `None`.
- `janito/agent/config.py`: Configuration management classes and `get_api_key()`.
- `janito/agent/runtime_config.py`: Defines the in-memory runtime config and `unified_config`, which always checks runtime (session) overrides before falling back to effective (local/global) config.
- `janito/agent/conversation.py`: Manages conversation history.
- `janito/agent/tool_handler.py`: Handles tool execution.
- `janito/agent/queued_tool_handler.py`: Tool handler subclass for streaming tool progress.

### Tools (`janito/agent/tools/`)
- `ask_user.py`: Tool to ask user questions. Uses a `prompt_toolkit` multiline input prompt with Esc+Enter submission, matching the chat interface style.
- `bash_exec.py`: Run bash commands, live output.
- `create_directory.py`: Create directories.
- `create_file.py`: Create files.
- `fetch_url.py`: Fetch webpage text.
- `find_files.py`: Recursive file search respecting .gitignore.
- `file_str_replace.py`: Replace exact string occurrences in a file with a new string.
- `gitignore_utils.py`: Uses the `pathspec` library to fully support `.gitignore` syntax (including negations, nested patterns, wildcards) for filtering ignored files and directories during file search.
- `move_file.py`: Move files/directories.
- `remove_file.py`: Delete files.
- `rich_live.py`, `rich_utils.py`: Terminal output formatting.
- `search_text.py`: Search text in files.
- `view_file.py`: View file contents or directory listing.
- `__init__.py`: Marks tools as a package.

## Templates
- `janito/templates/system_instructions.j2`: Jinja2 template for system prompt.

## Web Server Package: `janito.web`
- `janito/web/__init__.py`: Marks the web module as a package.
- `janito/web/__main__.py`: Web server entry point.
- `janito/web/app.py`: Defines the Flask app and API endpoints.
- `janito/web/templates/index.html`: Default index page served by Flask.
- `janito/web/static/app.js`: JavaScript for the web UI.
- `janito/web/static/style.css`: CSS styles for the web UI.
- `janito/web/docs/structure.md`: Duplicate or misplaced copy of the project structure documentation.

## Documentation
- `docs/structure.md`: Main documentation file explaining the purpose of each file and folder.

## Build Artifacts
- `build/`, `dist/`: Build output directories containing compiled packages and distribution archives.

## Removed Legacy Files
- `janito/chat.py`: An older standalone interactive chat loop implementation using `prompt_toolkit`. Removed as it was superseded by `janito.cli_chat_shell.chat_shell` and no longer used.
