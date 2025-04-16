**Note: This project requires Python 3.11 or newer.**

# Project Structure and Purpose

## Core Package: `janito`
- `janito/__init__.py`: Defines the package version (`__version__`).
- `janito/__main__.py`: Minimal CLI entry point. Delegates to `janito.cli.main.main()`.
- `janito/render_prompt.py`: Renders the system prompt using Jinja2. The logic is now static except for the 'role' variable.
- `janito/prompts/system_instructions.txt`: Alternative or plain text version of the system prompt instructions (for reference only).

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
  - `/system`: Show the current system prompt. The prompt is now always rendered in a static way except for the 'role' variable.
  - `/continue`: Restore the last saved conversation and CLI prompts from `.janito/last_conversation.json`.
  - `/reset`: Reset conversation history (clears in-memory state and deletes saved conversation).
  - `/config`: Show or set configuration from within the chat shell. Usage:
    - `/config show` — Show effective configuration (local, global, defaults)
    - `/config set local key=value` — Set a local config value
    - `/config set global key=value` — Set a global config value

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
  - Supports `--set-api-key` to save the API key globally (stored in `.janito/config.json`).
  - Also supports `--set-local-config key=val`, `--set-global-config key=val`, and `--show-config`.
  - Supports `--max-rounds` to override the maximum number of agent rounds per prompt or chat session (default: 50).
  - Supports `--max-tools` to limit the overall maximum number of tool calls within a chat session (default: unlimited).
  - The `--single-tool` flag and parallel tool call disabling have been removed.
  - The `edit_file` tool now reports missing TargetContent as an info message, not an error.
  - The `view_file` tool info output now shows `Lines (X-Y)` instead of `StartLine: X | EndLine: Y`.

- `janito/cli/config_commands.py`: Handles config-related CLI commands, including showing, setting, and saving config values. Now uses a helper (`_print_config.py`) to display config values, replacing the home directory with `~` for `system_prompt` if it starts with the user's home directory.
- `janito/cli/_print_config.py`: Helper for printing config items, with home directory shortening for `system_prompt`.
- `janito/cli/_utils.py`: Utility functions for CLI, including `home_shorten()`.
- `janito/cli/main.py`: Main CLI entry point. Handles argument parsing, config commands, and launches the CLI shell or web server.
- `janito/cli/runner.py`: Runs the CLI chat loop, manages agent setup, and handles prompt/system prompt logic.
- `janito/cli/logging_setup.py`: CLI logging configuration.

# Build & Release Automation

## Release Scripts
- `tools/release.sh`: Bash script for automated build and release to PyPI. Checks for required tools (`hatch`, `twine`), validates the version in `pyproject.toml` against PyPI and git tags, builds the package, and uploads to PyPI.
- `tools/release.ps1`: PowerShell script for Windows with the same logic as the Bash script.

## Usage
- **Linux/macOS:** `./tools/release.sh`
- **Windows:** `./tools/release.ps1`

These scripts ensure version consistency and automate the release process for maintainers.

# ... (rest unchanged)
