# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.26.0...HEAD)

Changes since `v4.26.0` (2026-08-17).

### Changed

- Pressing Ctrl+C while the `AskUser` tool is waiting for an answer now
  interrupts the in-flight LLM conversation turn (the agent loop rolls the
  conversation history back and returns to the prompt) instead of silently
  continuing with an empty answer. The `KeyboardInterrupt` propagates through
  the tool executor, so it is handled by the same cancel path as a Ctrl+C
  during streaming. Piped input / Ctrl+D at the prompt still yields an empty
  answer.
- The `/prompt` shell command and `janito --show-system-prompt` now only
  advertise skills in their titles (e.g. "(with skills)" / "(with Skills)")
  when a `skills` section is actually present; with no skills available the
  title is shown without the skills suffix.
- The `/prompt` shell command and `janito --show-system-prompt` now insert an
  empty row after each system-prompt section in the rendered table, providing
  a visual context split between the `start`, `skills`, `agents.md` and
  `plugins:<name>` sections.
- The system prompt is now assembled through a new `SysPromptManager` class
  (`janito/system_prompt.py`) that owns an ordered list of
  `(section_name, section_text)` sections (`start`, `skills`, `agents.md`,
  `plugins:<name>`).  All system-prompt manipulation (plugins, `SessionSetup`,
  the `/prompt` shell command and `janito --show-system-prompt`) now goes
  through the shared `SYSTEM_PROMPT_MANAGER`; `render()` joins the sections
  with a trailing newline per section for visual separation.  The previous
  module-level `get_system_prompt_with_skills`, `get_system_prompt_sections`
  and `register_plugin_system_prompt` helpers are removed, and the first
  section is named `start` (was `base`).
- The OneDrive functionality (tools, system prompt, authentication) was
  extracted from the core into the `janito-onedrive-plugin` plugin.  The
  `--onedrive`, `--onedrive-auth`, `--onedrive-logout` and `--onedrive-status`
  CLI flags are removed; use `--plugin ../plugins/janito-onedrive-plugin`
  (or install it to `~/.janito/plugins`).  When the plugin loads and the
  `azure_client_id` secret is configured, it runs the device code
  authentication flow automatically — set the secret with
  `janito --set-secret azure_client_id=your-client-id`, then restart janito.
  The `/onedrive` shell command provides `logout` and `status` subcommands
  (authentication is automatic, so there is no `auth` subcommand).  The
  OneDrive docs moved into the plugin's README.
- The version banner (`Janito x.y.z - Working at <cwd>`) is now printed
  before any plugin loading messages at startup, instead of only with the
  full-privileges warning.
- A plugin whose `on_start()` hook reports an error (e.g. the gmail plugin
  when the required secrets are missing) now **fails to load**: its tools,
  commands and system-prompt section are no longer registered.  Previously
  the error was recorded but the plugin's content was still activated.
- Plugin loading now prints `Loading plugin <name>` with `end=""` and then
  prints ` OK` or ` FAILED: <reason>` on completion, e.g.
  `Loading plugin janito-gmail-plugin OK` or
  `Loading plugin janito-gmail-plugin FAILED: missing required secret: gmail_username`.
- `--plugin` pointing to a missing directory (or a directory without an
  `__init__.py`) now reports a clear error
  (`plugin directory not found: <path> (check the path passed to --plugin)`
  / `plugin directory has no __init__.py: <path>`) instead of a confusing
  `No module named ...` from the import.
