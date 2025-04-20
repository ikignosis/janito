# Changelog

## [1.5.2] - 2025-04-19
### Changed
- Updated janito/agent/tools/find_files.py and search_files.py.

## [1.5.1] - 2025-04-19
### Changed
- Refactored tool import/registry logic for improved maintainability.
- Improved CLI chat shell UI for better user experience.
- Updated tool call handling logic for robustness.

### Other
- Bumped version to 1.5.1 in pyproject.toml.

---

(Previous changelog entries would appear here if available.)

## [Unreleased]
### Improved
- `run_bash_command` tool now returns actual stdout/stderr output directly if both are small (≤50 lines and ≤1000 characters each). If stderr is empty, it is omitted from the result. For large outputs, only file info is returned, and stderr file info is omitted if empty.

### Added
- Added `.pre-commit-config.yaml` for code linting, formatting, and spell-checking using ruff, black, and codespell.

## [Unreleased]
### Added
- Introduced `AgentProfileManager` for profile, role, interaction style, and system prompt management.
- Added support for multiple system prompt templates (e.g., default and technical) selected by interaction style.
- Refactored CLI and session logic to use the profile manager for all prompt/profile handling.

### Changed
- System prompt templating and interaction style logic are now handled outside the low-level Agent class.
- Improved separation of concerns between LLM agent execution and user/session profile management.

### Added
- You can now set the agent's `interaction_style` ("default" or "technical") globally or per-project via config files (`~/.janito/config.json` or `.janito/config.json`).
- Updated documentation in README.md, README_structure.txt, and docs/CONFIGURATION.md to describe the new config option and usage.
