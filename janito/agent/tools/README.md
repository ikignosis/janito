# README for janito.agent.tools

[This file is documentation and not meant to be compiled as Python.]

## Tools

- ask_user.py
- create_directory.py
- create_file.py
- fetch_url.py
- find_files.py
- get_file_outline.py
- get_lines.py
- gitignore_utils.py
- move_file.py
- py_compile_file.py
- remove_directory.py
- remove_file.py
- replace_text_in_file.py
- replace_file.py
- rich_live.py
- run_bash_command.py
- run_python_command.py
- search_files.py
- tools_utils.py

See each tool's section for usage and description.

## create_file
Creates a new file with the given content. Fails if the file already exists.
- Args: path (str), content (str)
- Returns: Success or error message.

## replace_file
Overwrites (replaces) a file with the given content. Creates the file if it does not exist.
- Args: path (str), content (str)
- Returns: Success message for creation or replacement.
