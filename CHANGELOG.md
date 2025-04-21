## [1.6.0] - 2024-06-09

### Features
- Added `replace_file` tool, which always overwrites (or creates) the file at the given path.
- ask_user tool now displays a status bar hint about pressing F12 to auto-fill 'proceed' and submit, improving user guidance.
- 'exit' (no slash) now exits the shell, same as '/exit'.
- Added --verbose-stream CLI flag to print raw OpenAI chunks during streaming.
- Added support for global and local interaction_style (default/technical) via config.
- Improved get_file_outline for Python files: nested element parsing, readable table output, type-aware summary for non-Python files.

### Improvements
- Improved system prompt: includes platform, Python version, shell/environment info, and path conventions.
- Refined prompt template system: clarified guidance for multi-region edits and destructive operations.
- Enhanced file reading/writing robustness (errors='replace', encoding='utf-8').
- Refactored search tools: removed max_results/return_all_matches, added max_depth param for directory traversal.
- Improved run_bash_command and run_python_command output handling and docs.
- Standardized and clarified instruction template sections and order.
- Improved documentation and structure (README_structure.txt, CHANGELOG.md, etc.).
- Added .pre-commit-config.yaml for code linting and formatting.

### Bug Fixes
- Fixed FileNotFoundError when creating files in current directory.
- Fixed chat shell hang on Ctrl+C by using prompt_toolkit for confirmation.
- Fixed OpenAI streaming event handling and client usage.
- Fixed tool registry: require callable .call, improved argument validation.

### Other Changes
- BREAKING: Removed the `overwrite` option from the `create_file` tool. It now only creates new files and fails if the file exists.
- Updated documentation and tool registry to reflect these changes.
- Refactored and reorganized CLI and agent modules for maintainability.
- Removed obsolete and legacy files.
