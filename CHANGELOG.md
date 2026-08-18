# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.26.0...HEAD)

Changes since `v4.26.0` (2026-08-17).

### Fixed

- The `google` provider is now marked `gemini_flavor: True` and no longer
  sends the `enable_thinking` extra-body flag to Google's
  OpenAI-compatibility layer.  Gemini 3.x models reason by default and the
  field does not exist in the request schema, so using `/thinking on` or
  `-t`/`--thinking` previously failed with a 400
  "Unknown name \"enable_thinking\": Cannot find field" error.  Thinking
  depth is instead controlled through `--reasoning-level` (sent as
  `reasoning_effort`, which the API maps to the model's `thinking_level`).
- The `google` provider now works with tool/function calls: Gemini 3.x
  requires each replayed function call in the conversation history to carry
  the `extra_content.google.thought_signature` the model issued with it, and
  the stream consumer previously dropped it, so the follow-up request after
  the first tool call failed with a 400
  "Function call is missing a thought_signature in functionCall parts" error.
  The signature is now captured from the streamed tool-call delta and echoed
  back verbatim in the assistant message (both CLI and web loops).
- The `/history` shell command now renders the actual conversation for
  stateless Responses providers (e.g. DeepSeek), whose full history is kept
  client-side as Responses input items in `conversation_items` instead of
  `messages_history`. Previously it showed only the system prompt. Tool-call
  rounds are shown as `function_call` / `function_call_output` rows, and for
  server-side Responses providers (e.g. OpenAI) any pending Enter-cancelled
  messages are shown after the system prompt.

### Added

- New `/thinking on|off` shell command to enable or disable runtime config
  thinking mode for the current session without altering the persisted
  configuration in `config.json`. Running `/thinking` alone displays the
  current session thinking status and usage instructions.
- New `/plugins` shell command lists the installed plugins (scanned from
  `<config_dir>/plugins`, default `~/.janito/plugins`), showing each
  plugin's name, path and whether it loaded in the current session (with
  `on_start` errors when the plugin failed to load). When no plugins are
  installed it prints install/load hints and the plugins directory path.
- New `--uninstall-plugin <name>` CLI flag removes an installed plugin's
  directory from the plugins dir (honoring `-c/--config-dir`), mirroring
  `--install-plugin`. The name is the plugin's actual **plugin name** (the
  `name` symbol the plugin exports, as shown by `--list-plugins`) — e.g.
  `janito --uninstall-plugin codesearch` removes the
  `janito-codesearch-plugin` directory. A broken plugin that cannot be
  imported is matched by its directory name as a fallback; a non-existent
  plugin reports an error and exits non-zero.
- New built-in `google` provider for Google Gemini models, accessed through
  Google's OpenAI-compatibility layer
  (`https://generativelanguage.googleapis.com/v1beta/openai/`). Its default
  model is `gemini-3.7-flash` (1M input / 64k output tokens,
  Chat Completions), with configurable reasoning levels
  `minimal`/`low`/`medium`/`high` (the OpenAI-compatible `reasoning_effort`
  mapping to the Gemini `thinking_level`). Set the Gemini API key from
  Google AI Studio with
  `janito --set-api-key="your-gemini-api-key" --provider google`.
- Added `janito/providers/google/cost.py` with a `get_cost(model, input,
  output, cached)` helper that estimates the monetary cost of a request from
  the per-1M-token rates for `gemini-3.7-flash` ($0.75 / $0.1875 context cache
  read / $3.75 output), billing cached input tokens at the context cache read
  rate and formatting the result as `NN.DDDDDD$` (e.g. `\"4.500000$\"`); unknown
  models fall back to `\"N/A\"`. There is no peak-hour surcharge. The module
  docstring documents the rates source (https://ai.google.dev/pricing).
  (`janito/providers/google/cost.py`, `tests/test_provider.py`,
  `tests/test_input_tokens_info.py`)
- `--verbose` (`-v`) now also dumps the actual API request parameters and a
  compact response summary for every streaming round (Chat Completions,
  Responses, Anthropic and DashScope). The request panel shows the scalar
  parameters and, because the conversation history is too long to dump in
  full, only the **tail** of `messages`/`input` (last 3 entries, each string
  truncated) plus the total item count and the tool names; the response panel
  shows the content/reasoning tail, tool-call names, normalized token usage,
  the server-side response id when the API reports one, and every raw
  top-level response attribute (e.g. `id`, `model`, `created`/`created_at`,
  `system_fingerprint`, `status`, `finish_reason`/`stop_reason`,
  `request_id`) enumerated on its own `Raw <attr>:` line. Works in both
  single-prompt (`janito -v \"...\"`) and interactive (`janito -v`) modes.
  (`janito/openai_client/client_support.py`,
  `janito/openai_client/base_client.py`, `tests/test_clients.py`)

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
