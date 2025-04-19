Project Structure
=================

Root Files:
- ARCHITECTURE.md
- AZURE_OPENAI.md
- CHANGELOG.md
- CONFIGURATION.md
- LICENSE
- MESSAGE_HANDLER_MODEL.md
- pyproject.toml
- README.md
- README_DEV.md
- RELEASE_NOTES_1.3.md
- RELEASE_NOTES_1.4.md
- RELEASE_NOTES_1.5.md
- requirements.txt

Directories:
- dist/
    - janito-1.4.1.tar.gz
    - janito-1.4.1-py3-none-any.whl
- docs/
    - cli_model_override.md
    - cli_reload_command.md
- janito/
    - __init__.py, __main__.py, render_prompt.py, rich_utils.py
    - agent/
        - agent.py, config.py, config_defaults.py, config_utils.py, content_handler.py, conversation.py, message_handler.py, queued_message_handler.py, rich_tool_handler.py, runtime_config.py, tool_registry.py, __init__.py
        - templates/
            - system_instructions.j2
        - tools/
            - append_text_to_file.py, ask_user.py, fetch_url.py, file_ops.py, find_files.py, get_file_outline.py, get_lines.py, gitignore_utils.py, python_exec.py, py_compile.py, remove_directory.py, replace_text_in_file.py, rich_live.py, run_bash_command.py, search_files.py, tools_utils.py, tool_base.py, utils.py, __init__.py, README.md
    - cli/
        - main.py, arg_parser.py, config_commands.py, logging_setup.py, runner.py, _print_config.py, _utils.py, __init__.py
    - cli_chat_shell/
        - chat_loop.py, commands.py, config_shell.py, load_prompt.py, session_manager.py, ui.py, __init__.py
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
