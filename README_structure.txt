Project Structure
=================

Root Files:
- LICENSE
- pyproject.toml
- README.md
- requirements.txt


Directories:
- docs/
    - ARCHITECTURE.md
    - AZURE_OPENAI.md
    - CHANGELOG.md (now at project root, was docs/CHANGELOG.md)
    - CONFIGURATION.md
    - MESSAGE_HANDLER_MODEL.md
    - README_DEV.md
- dist/
- docs/
- janito/
    - __init__.py, __main__.py, render_prompt.py, rich_utils.py
    - agent/
        - agent.py, config.py, config_defaults.py, config_utils.py, content_handler.py, conversation.py, message_handler.py, openai_schema_generator.py, queued_message_handler.py, rich_tool_handler.py, runtime_config.py, tool_registry.py, __init__.py
        - templates/
            - system_instructions.j2
        - tools/
            - append_text_to_file.py, ask_user.py, create_directory.py, create_file.py, fetch_url.py, find_files.py, get_file_outline.py, get_lines.py, gitignore_utils.py, move_file.py, python_exec.py, py_compile.py, remove_directory.py, remove_file.py, replace_text_in_file.py, rich_live.py, run_bash_command.py, search_files.py, tools_utils.py, tool_base.py, utils.py, __init__.py, README.md
    - cli/
        - main.py, arg_parser.py, config_commands.py, logging_setup.py, runner.py, _print_config.py, _utils.py, __init__.py
    - cli_chat_shell/
        - chat_loop.py, config_shell.py, load_prompt.py, session_manager.py, ui.py, __init__.py
    - commands/ (package, was commands.py)
        - __init__.py: Command handlers and dispatcher for chat shell commands.
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


- janito/agent/templates/system_instructions_technical.j2: Technical system prompt template for developer/engineer interaction style.
- janito/render_prompt.py: Now supports selecting prompt template by interaction style ("default" or "technical").
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
