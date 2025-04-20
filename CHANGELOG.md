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
