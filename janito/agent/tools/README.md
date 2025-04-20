# Agent Tools

This directory contains built-in tools for file operations, shell commands, user interaction, and more. Each tool is implemented as a class inheriting from `ToolBase` and is registered with the system for dynamic invocation.

For instructions on adding new tools, see the [Developer Guide](../../../docs/README_DEV.md).
For how tools fit into the system, see the [Architecture Guide](../../../docs/ARCHITECTURE.md).

## Tool List & Descriptions

### ask_user.py
**Description:**  
Ask the user a question and return their response via the CLI.  
**Usage:**  
- `question` (str): The question to ask the user.

### fetch_url.py
**Description:**  
Fetch the content of a web page and extract its text.  
**Usage:**  
- `url` (str): The URL to fetch.  
- `search_strings` (list[str], optional): Strings to search for in the page content; returns snippets around matches.

### file_ops.py
**Description:**  
(Utility functions for file operations, not a direct tool.)

### find_files.py
**Description:**  
Find files in a directory matching a pattern.  
**Usage:**  
- `directory` (str): Directory to search.  
- `pattern` (str): Filename pattern (e.g., `*.py`).  
- `recursive` (bool, default False): Search subdirectories.  
- `max_results` (int, default 100): Maximum number of results.

### get_file_outline.py
**Description:**  
Get an outline of a file's structure (non-empty lines).  
**Usage:**  
- `file_path` (str): Path to the file.

### get_lines.py
**Description:**  
Get specific lines from a file. If both `from_line` and `to_line` are omitted, the entire file is returned in one call—no need to chunk or split requests when reading the full file.  
**Usage:**  
- `file_path` (str): Path to the file.  
- `from_line` (int, optional): Start line (1-based).  
- `to_line` (int, optional): End line (inclusive).

### gitignore_utils.py
**Description:**  
(Utility functions for .gitignore handling, not a direct tool.)

### run_python_command.py
**Description:**  
Execute Python code in a separate process and capture output.  
**Usage:**  
- `code` (str): The Python code to execute.

### py_compile_file.py
**Description:**  
Validate a Python file by compiling it with py_compile_file.  
**Usage:**  
- `file_path` (str): Path to the Python file.  
- `doraise` (bool, optional): Raise exceptions on errors.

### remove_directory.py
**Description:**  
Remove a directory.  
**Usage:**  
- `directory` (str): Path to the directory.  
- `recursive` (bool, optional): Remove recursively.

### append_text_to_file.py
**Description:**  
Append the given text to the end of a file.
**Usage:**  
- `file_path` (str): Path to the file.  
- `text_to_append` (str): Text to append to the file.

### replace_text_in_file.py
**Description:**  
Replace exact occurrences of a given text in a file.  
**Usage:**  
- `file_path` (str): Path to the file.  
- `search_text` (str): Text to search for (must include indentation if present).  
- `replacement_text` (str): Replacement text (must include desired indentation).  
- `replace_all` (bool, default False): Replace all occurrences or just the first.

### run_bash_command.py
**Description:**  
Execute a non-interactive bash command and capture live output. If the output is small (≤50 lines and ≤1000 characters for both stdout and stderr), the actual output is returned directly. If stderr is empty, it is omitted from the result. For larger outputs, only the file locations and line counts are returned (stderr file info is omitted if empty).  
**Usage:**  
- `command` (str): The bash command to run.  
- `timeout` (int, default 60): Timeout in seconds.  
- `require_confirmation` (bool, default False): If True, require user confirmation.

### search_files.py
**Description:**  
Search for a text pattern in all files within a directory and return matching lines.  
**Usage:**  
- `directory` (str): Directory to search.  
- `pattern` (str): Text pattern to search for.

---

All tools are registered automatically and can be invoked via the agent interface. For implementation details, see each tool's Python file.

> **Note:** When adding a new tool, follow the requirements in [../../README_DEV.md](../../README_DEV.md) for registration and documentation. Update this file with a description and usage for your tool.

---

> **Note:** Tool descriptions are now generated from the tool class docstring (as a prefix) and the `call` method docstring summary. Ensure your class docstring is clear and user-facing.
