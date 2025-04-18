# Changelog

## [1.4.1] - 2025-04-19
### Changed
- Updated project version to 1.4.1.
- See RELEASE_NOTES_1.4.md for details.

## [Unreleased]

### Changed
- Conversation spinner now formats word counts with 'k'/'m' suffixes for improved readability.
- fetch_url tool: Improved output formatting for status and success messages.
- file_ops tool: Enhanced success messages for file creation and updating, now showing line counts and clearer feedback.

### Removed
- file_ops tool: Removed the RemoveFileTool class.


## [1.5.x] - 2025-04-18

### Added
- Instructions in README for obtaining an API key from OpenRouter.
- Reference to Azure OpenAI usage and new AZURE_OPENAI.md file.

### Changed
- Minor improvements to output and warning messages in various tool files (fetch_url, file_ops, find_files, get_file_outline, get_lines, py_compile, python_exec, remove_directory, replace_text_in_file, search_files).

## [1.4.0] - 2025-04-18

### Added
- `--max-tools` CLI/config parameter to limit the overall maximum number of tool calls within a chat session.
- New tool: `get_file_outline` for outlining file structure.
- Release notes for 1.4 (`RELEASE_NOTES_1.4.md`).

### Changed

#### Tools
- run_bash_command: Now prints live output to the user and always stores stdout/stderr in temp files with a run_bash_ prefix. The result message shows file paths and line counts for both stdout and stderr, and instructs to use get_lines for details. Switched from multiprocessing to direct subprocess/thread-based output handling. Improved error handling and output formatting.
- fetch_url: Removed the unused on_progress callback parameter; now uses internal progress updates.
- gitignore_utils: Improved path handling with expand_path and ensured UTF-8 encoding for .gitignore file reading; improved robustness.
- py_compile: Now prints success and error messages using print_success and print_error.
- python_exec: Removed the unused on_progress callback parameter.
- rich_utils: print_info, print_success, and print_error now accept an end parameter for better output control.
- __init__.py: Tools are now dynamically imported from the directory, simplifying tool registration.

- Updated the README documentation for clarity and new features.
- Improved configuration documentation and examples.
- `view_file` tool info output now shows `Lines (X-Y)` instead of `StartLine: X | EndLine: Y`.
- "TargetContent not found" in `edit_file` tool is now an info message, not an error.
- Refined system instructions for tool usage and editing guidance.
- Updated project version to 1.4.0.

### Removed
- `--single-tool` CLI/config parameter and all related logic/documentation (parallel tool call disabling).

### Internal/Refactor
- Refactored `ToolHandler` and related registration logic for improved maintainability.
- Updated `README_structure.txt` to reflect new/removed files and structure changes.

### Fixed
- Fixed: run_bash_command could hang in some scenarios; switching to thread-based output handling resolved this issue.


