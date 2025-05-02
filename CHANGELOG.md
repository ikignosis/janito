# Changelog

## [1.9.0] - 2025-05-02

### Added
- _Describe new features, enhancements, and fixes here._

---

## [1.8.0] - 2025-04-28

### Documentation
- Major updates and new guides added, including code intelligence, prompting, and tool usage.
- Improved structure and clarity across docs, with new images and reference material.

### Agent Core
- Significant refactor and modularization of the event and message handling system.
- New event-driven architecture introduced for better extensibility and maintainability.
- Expanded protocol and handler support for agent actions.

### Tools
- Many new tools added for file, directory, and text operations, as well as improved tool documentation.
- Enhanced tool registry and execution tracking for more robust tool management.

### CLI
- Updates to argument parsing, logging, and runner utilities for a smoother CLI experience.
- New terminal web starter (termweb) introduced for launching a web-based terminal interface.

### Termweb
- Added a web-based terminal interface for interacting with the agent in-browser.
- Includes static assets, quick open, and improved user experience for web terminal sessions.

### Internationalization
- Initial support for multiple languages, including Portuguese, with message files and translation structure.

### Configuration & Profiles
- Refined configuration defaults and profile management for easier setup and customization.

### Miscellaneous
- General improvements to code quality, documentation, and developer tooling.
- Various bug fixes and minor enhancements throughout the codebase.

---

## [1.7.0] - 2025-04-22

### Features
- Added a [docs] optional dependency group for documentation building with MkDocs. Install with: `pip install .[docs]`
- F12 rotation: Cycle through short instructions ('proceed', 'go ahead', 'continue', 'next', 'okay') on F12 keypress in CLI and ask_user tool.
- Added shell detection utility and improved shell/environment handling.
- Include all files in janito.agent.templates for packaging (including .txt.j2 files).

### Improvements
- Unified find_files and search_files signatures, set recursive=True by default, removed max_depth param, and updated docstrings for consistency.
- Improved memory tool: missing key now returns warning (⚠️) instead of error (❗); updated docstring standard and tests; ensured OpenAI function schema compatibility.
- Print template search paths to stderr on Jinja2 TemplateNotFound in CLI prompt loading.
- Explicitly specify UTF-8 encoding in open() calls for config and web modules.
- Set default Azure OpenAI API version everywhere for consistency.
- Enhanced run_command stream_reader to ensure utf-8 decoding with errors=replace for live output.
- Refactored and cleaned up code for maintainability and linting (removed unused imports, auto-formatting, etc.).

### Bug Fixes
- Fixed broken link to costs.md after docs reorganization.
- Fixed pyproject.txt.j2 packaging issues.
- Fixed CLI toolbar display by making last_usage_info reactive.

### Documentation
- Major documentation overhaul: improved structure, navigation, and branding (SVG logo, architecture docs, API docs, etc.).
- Added and updated many documentation files in docs/ directory.
- README and docs now cross-link to each other and to janito.dev for high-level overview.

### Other Changes
- Removed check for .janito/tech.txt in CLI runner (temporary workaround).
- Restored files after interrupted rebase and manual backup/restore.
- Updated packaging and requirements for consistency.

## [1.6.0] - 2024-06-09

### Features
- BREAKING: Removed `replace_file` tool. `create_file` now supports an `overwrite` parameter for updating files.
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
- BREAKING: Restored and improved the `overwrite` option for `create_file`. Use `overwrite=True` to update files if they exist.
- Updated documentation and tool registry to reflect these changes.
- Refactored and reorganized CLI and agent modules for maintainability.
- Removed obsolete and legacy files.
