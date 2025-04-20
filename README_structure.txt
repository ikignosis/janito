Project Structure
=================

Root Files:
- LICENSE
- pyproject.toml (version: 1.6.0-dev)
- README.md (Current Version: 1.6/dev)
- requirements.txt


Directories:
- docs/
    - ARCHITECTURE.md
    - AZURE_OPENAI.md

    - CONFIGURATION.md
    - MESSAGE_HANDLER_MODEL.md
    - README_DEV.md

- docs/
- janito/
    - __init__.py, __main__.py, render_prompt.py, rich_utils.py
    - agent/
        - agent.py, config.py, config_defaults.py, config_utils.py, content_handler.py, conversation.py, message_handler.py, openai_schema_generator.py, queued_message_handler.py, rich_tool_handler.py, runtime_config.py, tool_registry.py, __init__.py
        - templates/
            - system_prompt_template.j2
        - tools/
            - append_text_to_file.py, ask_user.py, create_directory.py, create_file.py, fetch_url.py, find_files.py, get_file_outline.py, get_lines.py, gitignore_utils.py, move_file.py, py_compile_file.py, remove_directory.py, remove_file.py, replace_text_in_file.py, rich_live.py, run_bash_command.py, search_files.py, tools_utils.py, utils.py, __init__.py, README.md
    - cli/
        - main.py, arg_parser.py, config_commands.py, logging_setup.py, runner.py, _print_config.py, _utils.py, __init__.py
    - cli_chat_shell/
        - chat_loop.py, config_shell.py, load_prompt.py, session_manager.py, ui.py, __init__.py
    - cli_chat_shell/
        - commands/
            - __init__.py: Command dispatcher for chat shell commands.
            - session.py: Conversation/session-related commands (e.g., /continue, /history)
            - system.py: System prompt, role, and style commands (e.g., /system, /role, /style)
            - session_control.py: Session control commands (e.g., /exit, /restart)
            - utility.py: Utility commands (e.g., /help, /clear, /multi)
            - config.py: Config and reload commands (e.g., /config, /reload)
            - history_reset.py: Conversation reset command (e.g., /reset)
    - web/
        - app.py, __init__.py, __main__.py
        - static/
            - eslint.config.js, favicon.ico
            - css/
                - fireworks.css, layout.css, modal.css, sidebar.css, terminal.css
            - js/
                - fireworks.js, main.js, modal.js, progressFormatter.js, sessionControl.js, stream.js, terminal.js, toolProgress.js
        - templates/
            - index.html
- tools/
    - release.ps1, release.sh
- janito/agent/openai_schema_generator.py


- janito/agent/templates/profiles/: Contains base and main style templates.
    - system_prompt_template_base.j2: Base system prompt template, extended by all styles.
    - system_prompt_template.j2: Default system prompt template (extends base).
    - system_prompt_template_technical.j2: Technical system prompt template for developer/engineer interaction style (extends base).
- janito/agent/templates/features/: Contains feature extension templates.
    - system_prompt_template_autocommit.j2: Feature extension template for 'autocommit' (extends main style).
- janito/render_prompt.py: Now supports combinatorial style selection (e.g., 'technical-autocommit') and template layering.
- janito/cli_chat_shell/commands/: Now supports selecting system prompt template by agent.interaction_style ("default" or "technical").
- janito/agent/profile_manager.py: Manages user profile, role, interaction style, and system prompt selection. Instantiates and manages the low-level Agent.
- janito/cli_chat_shell/commands/: Now uses AgentProfileManager for system prompt, role, and interaction style management.
- janito/cli/runner.py: CLI now instantiates AgentProfileManager and wires interaction style and role.
- janito/cli_chat_shell/chat_loop.py: Chat shell uses profile_manager for agent, prompt, and command handling.
- janito/cli/arg_parser.py: Adds --style CLI argument for interaction style selection (was --interaction-style).
- janito/cli/runner.py: Uses args.style for interaction style.
- janito/cli_chat_shell/ui.py: Toolbar now displays current interaction style (style).
- janito/cli_chat_shell/commands/: Adds /style command to change interaction style at runtime.

- Global and local configuration now support the `interaction_style` key ("default" or "technical") to control agent behavior and prompt style. See docs/CONFIGURATION.md and README.md for usage.

- janito/cli_chat_shell/commands/: Adds /set command as an alias for /config set. Usage: /set local|global key value

- /config shell command now warns that /restart may be required for config changes to take effect.
- docs/CONFIGURATION.md updated to mention /restart after config changes in the shell.

- CLI now supports --trust-tools/-T flag and 'trust_tools' config (global/local):
    - When enabled, suppresses all tool output (including rich handler output), only shows output file locations.
    - Can be set via CLI (--trust-tools/-T), global config, or local config.
    - CLI flag takes precedence over config.
    - See janito/cli/arg_parser.py, janito/agent/config.py, janito/agent/rich_tool_handler.py for implementation details.
- CLI now supports --verbose-events:
    - Prints all agent events before dispatching to the message handler (for debugging).
agent/tool_base.py, 
Combinatorial Style System:
--------------------------
- The agent now supports combinatorial styles using a main style (e.g., 'default', 'technical') and optional feature extensions (e.g., 'autocommit').
- Style strings are specified as 'mainstyle-feature1-feature2', e.g., 'technical-autocommit'.
- The main style template is extended by each feature template in order, allowing feature-specific overrides.
- See janito/render_prompt.py for implementation and janito/agent/templates/ for template structure.

- Platform detection is now included in the system prompt context (variable: platform, e.g., 'windows', 'linux', 'darwin').
- The <platform> section in the base template instructs the agent to use platform-appropriate path conventions.

## [1.6.0-dev] Ensured PYTHONUTF8 is set for all CLI and web entry points
- janito/cli/main.py: Now sets PYTHONUTF8=1 at startup and re-execs on Windows if needed for UTF-8 safety.
- janito/web/__main__.py: Now sets PYTHONUTF8=1 at startup and re-execs on Windows if needed.
- janito/__main__.py: CLI entry point unchanged (delegates to janito.cli.main.main).
- All CLI and web invocations now guarantee UTF-8 mode for Python, improving Unicode reliability on Windows.

# generated by janito.dev