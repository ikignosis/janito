# Changelog

## [1.3.0] - Unreleased

### Changed

### Fixed
- Cleaned up legacy code and improved config validation logic.

---

## [1.2.0] - Unreleased

### Added
- CLI: Added `--model` argument to allow temporary model override for a single session (does not persist to config).
- Documentation: Added `docs/cli_model_override.md` explaining the new `--model` CLI override behavior.

### Changed
- Default model changed from `openrouter/optimus-alpha` to `openai/gpt-4.1` in:
  - `janito/agent/config_defaults.py`
  - `janito/agent/README.md`
  - `janito/agent/config.py`
  - `README.md` and config documentation tables
- CLI and agent instantiation now always use the model from the unified config, which checks runtime/session overrides first.

### Fixed
- Improved CLI runner to always fetch model from the unified config, ensuring session overrides are respected.
- Minor documentation and help text updates.

---

## [1.1.1] - Previous release
- See earlier tags for details.
