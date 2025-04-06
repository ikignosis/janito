- `aurora/agent/config.py`: Defines configuration management classes:
  - `FileConfig` loads and saves JSON configs (local and global)
  - `RuntimeConfig` is an in-memory, reset-on-restart config
  - `EffectiveConfig` provides a merged, read-only view of runtime, local, and global configs, with priority order runtime > local > global
  - Singleton instances: `runtime_config`, `local_config`, `global_config`, and `effective_config`

Other files:

- `create_file.py`: Tool to create a file with specified content. Supports an `overwrite` parameter (default False) to control overwriting existing files. When replacing, it reports the number of lines in the old and new content.
- `remove_file.py`: Tool to delete files.
- `move_file.py`: Tool to move a file or directory from a source path to a destination path. Supports an `overwrite` parameter to replace the destination if it exists.
- `view_file.py`: Tool to view the contents of a file or list directory contents. Accepts `start_line` (1-based, default 1) and `end_line` (inclusive, optional). Displays total number of lines in the file and does not truncate output. The start message includes 'View' before the path.
- `find_files.py`: Recursively finds files matching a glob pattern within a directory, **skipping files and directories ignored by `.gitignore`** if present.
- `search_text.py`: Searches for a regex pattern inside files matching a glob pattern, recursively within a directory, **skipping files and directories ignored by `.gitignore`** if present. Returns matches with filename, line number, and matched line. **No limit on the number of matches returned.**
- `gitignore_utils.py`: Utility functions to load `.gitignore` patterns, check if a path is ignored, and filter directory listings accordingly.
- `bash_exec.py`: Tool to execute Bash commands. Prints output to the terminal immediately as it is received from the running process, capturing both stdout and stderr live. **stdout is printed with white text on a blue background, stderr with white text on a red background, both on a dark background**. Returns the combined output and the return code after completion.

# CLI Entry Point
- `aurora/__main__.py`: Main CLI entry point. Parses command line arguments, including:
  - `prompt`: The user prompt (positional or stdin)
  - `-s/--system-prompt`: Optional override for the entire system prompt string
  - `-r/--role`: Override the role used in the system prompt template (default: 'software engineer')
  - `--verbose-http`, `--verbose-http-raw`, `--verbose-response`, `--show-system`, `--verbose-tools`: Various debug and display options
  - `--set-local-config key=val`: Set a key-value pair in the local config file `.aurora/config.json` and exit
  - `--set-global-config key=val`: Set a key-value pair in the global config file `~/.aurora/config.json` and exit
  - `--show-config`: Display the effective configuration, showing the source (local or global) for each key, then exit
  - `--version`: Show the program's version number and exit

  It loads the API key, renders the system prompt (with optional role override), initializes the agent, and handles interaction.

- `aurora/__init__.py`: Defines the package version (`__version__`).

# Web Server Package
- `aurora/web/__init__.py`: Marks the `web` directory as a Python package.
- `aurora/web/__main__.py`: Entry point to start a simple HTTP server. Can be run with `python -m aurora.web [port]` (default port 8000). Serves static files including `index.html` if present.
- `aurora/web/app.py`: Placeholder for the future web application logic that will provide similar capabilities to the CLI.
- `aurora/web/index.html`: The default index page served by the web server, providing a welcome message for the Aurora Web App.
