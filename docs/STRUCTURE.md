# Project Structure

## Main Directories
- `janito/`: Main package directory
  - `__init__.py`: Package initialization
  - `__main__.py`: Entry point for the package
  - `callbacks.py`: Callback functions
  - `config.py`: Configuration settings
  - `token_report.py`: Token reporting functionality
  - `cli/`: Command-line interface components
    - `__init__.py`: Package initialization
    - `agent.py`: Agent initialization and query handling
    - `app.py`: Main CLI application
    - `commands.py`: Command handling logic
    - `output.py`: Output formatting
    - `utils.py`: Utility functions
  - `data/`: Data files and resources
  - `tools/`: Tool implementations
    - `find_files.py`: Tool to find files matching patterns
    - `search_text.py`: Tool to search for text in files
    - `delete_file.py`: Tool to delete files
    - `replace_file.py`: Tool to replace file contents
    - `move_file.py`: Tool to move files
    - `prompt_user.py`: Tool to prompt for user input
    - `str_replace_editor/`: String replacement editor implementation
    - `fetch_webpage/`: Web page fetching functionality
- `.janito/`: Local configuration and data directory
  - `config.json`: Local configuration file
  - `last_message.json`: Last conversation (for backward compatibility)
  - `last_messages/`: Directory storing all conversation history
    - `{message_id}.json`: Individual conversation files with unique IDs
- `tests/`: Test files
- `tools/`: Project utility scripts
- `docs/`: Documentation files
  - `STRUCTURE.md`: This file, documenting the project structure

## Configuration Files
- `pyproject.toml`: Project configuration
- `requirements.txt`: Project dependencies
- `LICENSE`: License information
- `README.md`: Project overview with usage instructions and features
- `README_DEV.md`: Developer documentation