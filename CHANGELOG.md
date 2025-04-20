# Changelog

## [Unreleased]

### Refactored
- Moved ToolBase to `janito/agent/tool_base.py` to break circular import between tool modules and registry.
- Updated all tool and registry imports to use the new location.
- Removed old `tools/tool_base.py` and `tool_auto_imports.py`.
- Added `__all__` to `tools/__init__.py` for Ruff compliance.
- All tests passing after refactor.


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

## [Unreleased]
### Changed
- Refactored and reorganized the `janito/cli_chat_shell/commands/` package:
    - Split command handlers into logical modules: `session.py`, `system.py`, `session_control.py`, `utility.py`, `config.py`, and `history_reset.py`.
    - `__init__.py` now acts as the command dispatcher, importing handlers from submodules.
    - Updated `README_structure.txt` to reflect the new structure.
- Removed legacy/backup command handler file.

## [Unreleased]
### Changed
- Refactored all message handlers (rich, queued, base) to require dicts with 'type' and 'message' keys. Removed support for non-dict/plain string messages; TypeError is now raised if violated.
- Updated conversation event dispatch to always wrap content as dicts.
- Ensured trust and markdown logic is always applied consistently in rich handler.
- Improves robustness and traceability of event routing.
- Affected modules: janito/agent/rich_tool_handler.py, janito/agent/conversation.py, janito/agent/message_handler.py, janito/agent/queued_message_handler.py

### Other
- Bumped version to 1.6.0-dev in pyproject.toml and janito/__init__.py.

### Changed
- Updated system prompt templates to remove negated phrasing about minimal/single-region changes. Now directly encourages larger, multi-region, or reorganizational edits when appropriate, and replaces "Avoid excessive chunking" with "Avoid unnecessary splitting of text ranges" for clarity.
- Affected files: `janito/agent/templates/profiles/system_prompt_template_base.j2`, `janito/agent/templates/profiles/system_prompt_template_technical.j2`

## [Unreleased]
### Changed
- Updated `janito/agent/templates/features/system_prompt_template_allcommit.j2` to clarify allcommit behavior after successful operations.
- Revised `janito/agent/templates/profiles/system_prompt_template_base.j2` and `system_prompt_template_technical.j2` to clarify guidance on multi-region edits and documentation updates.
- Improved documentation in `janito/agent/tools/README.md` for tool usage and registration.
- Enhanced `janito/agent/tools/search_files.py` for robustness and clearer warnings.
- Reformatted `janito/cli/runner.py` for style compliance (black), no functional changes.
