# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.12.0...HEAD)

Changes since `v4.12.0` (2026-07-26).

### Added

- CLI: add `-f`/`--force` to `--set-api-key` to overwrite an already-stored API key without the confirmation prompt (intended for scripts and other non-interactive use).
- Web settings: the drawer now features a **provider combobox** that lists every supported provider with its effective configuration — resolved base URL (endpoint override or built-in default), configured model, API-key status (set/not set, never the key itself) and an `active` marker. Selecting a provider shows a detail card; the old read-only provider text field is gone. Backed by an enriched `GET /config/providers` endpoint that aggregates data from `provider_config`, `general_config` and `auth_config`.
- Web UI: add semantic CSS utility classes (`.pre-wrap`, `.muted`, `.flex-1`, `.padded`, `.gap-sm`, `.push-end`, `.warning-text`, `.message-error`, `.drawer-actions`, `.fine-print`, provider-detail styles, …) so the markup no longer relies on inline `style` attributes.
- Tests: add `tests/test_search_path_normalization.py` pinning down that `SearchText`/`SearchRegex` report cwd-relative paths in their results.
- `FindFiles` tool: new file-search tool that finds files and directories by name pattern and attributes (type, size, modification time, recursion depth, result limits, sorting), matching patterns against the full relative path — the equivalent of the Unix `find` command.
- CLI: add `-p` as a short alias for the `--provider` option.
- `GetCurrentTime` tool: returns the current date and time in ISO 8601 format with local/UTC representations and timezone info ([068625d](https://github.com/joaopinto/janito/commit/068625d)).
- Project-specific instructions: automatically load an `AGENTS.md` file from the current working directory and append its content to the system prompt under a "Project-Specific Instructions" section.
- Repository: add an `AGENTS.md` instructing agents to read `docs/TOOL.md` before creating a new tool, and to add `closes #n` to commit messages when working on GitHub issues.
- `RunGitHubCLI` tool: new system tool that executes the GitHub CLI (`gh`) to interact with GitHub artifacts, streaming command output in real time (like `RunBashCode`) and returning the captured stdout/stderr and exit code. The `gh` executable is located on PATH or in well-known install locations, and the tool is only loaded when it is available.
- Tests: add `tests/test_get_url.py` covering the `GetUrl` oversized-content temp-file handling (local HTTP server, no external network access).
- Tool usage tracking: record every tool invocation in a SQLite database (`tools_use.db` in the config directory) with per-tool counters, from both the CLI agent loop and the web backend; includes the `janito.tooling.tools_usage` module (with a small CLI to inspect counts) and tests.
- `SearchRegex` tool: new `respect_gitignore` parameter (default `True`) with a `--no-gitignore` CLI flag; search results now report `gitignore_applied` and `files_ignored_by_gitignore` counts.
- Skills: discover skills from a **local** directory (`.janito/skills/` in the current working directory) in addition to the **home** directory (`<config_dir>/skills/`); local skills take precedence over home skills with the same name, allowing project-specific overrides. Each `Skill` now tracks its `path` and `source` (`"home"` or `"local"`), and `list_skills()` exposes both. Backward-compatible: bare `Path` entries in `skill_paths` default to source `"home"`.
- Web chat: F2 / restart support — pressing F2 in the web chat clears the conversation history on both server and client while preserving the system prompt, mirroring the shell's F2 behaviour. The backend handles a new `restart` WebSocket message type (calling `ConversationSession.restart()`) and replies with a `restarted` acknowledgement; the frontend resets its local UI immediately and updates on the acknowledgement.
- Web chat: cancel/abort in-flight generation with Ctrl+C — pressing Ctrl+C while a response is being generated sends a `{"type": "cancel"}` WebSocket message that aborts the agentic loop on the server; the backend runs the stream and a cancel-listener concurrently via `asyncio.wait`, injects placeholder tool results for any dangling tool calls so the conversation history stays valid, and replies with a `cancelled` event; the frontend finalizes the assistant message with a "Generation stopped by the user" notice and resets the UI to idle. F2/restart now cancels any in-flight request first. A processing spinner is also shown at the bottom of the chat area while a request is in flight.
- Web chat: session status indicators in the sidebar — a spinner is shown while a background (non-active) session is processing (waiting, streaming, or running a tool), and a dot is shown when it finishes; indicators are cleared when the user switches to that session. A `janito-session-status` custom event broadcasts per-session status changes from `chat.js` to `sessions.js`, and all statuses are re-broadcast on tab switch so sessions already processing in the background get their indicators immediately.

### Changed

- CLI: `--set-api-key` no longer strictly requires `--provider`. When `--provider` is omitted, the configured default provider is used (the `provider` value from `config.json`, then the auth-store default); the command errors out only when no default provider is configured at all. Existing behaviour with an explicit `--provider` is unchanged. Adds fallback tests to `tests/test_set_api_key_overwrite.py`.
- CLI: `--set-api-key` now warns and prompts for confirmation before overwriting an already-stored API key for a provider. The prompt defaults to *no* (Enter keeps the existing key); decline to leave the key untouched. When stdin is not interactive and `--force` is not supplied, the overwrite is refused with a hint. Adds `tests/test_set_api_key_overwrite.py`.
- OpenAI client: the "💭 Reasoning" panel now renders reasoning content as Markdown (via `rich.Markdown`) instead of plain text, so structured reasoning output is displayed with formatting.
- `SearchText` and `SearchRegex` tools: match lines and count-only result keys are now normalized with `norm_path()`, so results report cwd-relative paths (e.g. `./subdir/file.py:3: …`) consistent with `ReadFile`, `ListFiles` and `FindFiles` instead of leaking absolute paths.
- Web backend: split the monolithic `web/backend/agent.py` (420 lines) into an `agent` package with focused modules — `tooling.py` (tool discovery + execution), `call.py` (OpenAI call parameters + stream accumulation), `turn.py` (the tool-call leg of a turn) and `loop.py` (the `stream_prompt()` orchestration skeleton).
- Web backend: refactor `events.py` so every event dataclass carries its own `to_dict()` serializer (with a `type` ClassVar) and `event_to_dict()` becomes a thin dispatcher; `routers/chat.py` is decomposed into small helpers (`_send_session_greeting`, `_read_client_message`, `_rollback`, `_run_turn`, `_accept_session`) so the WebSocket loop reads top to bottom; `routers/config.py` shares privileges serialization via `_privileges_dict()`.
- Web frontend: split the 840-line `theme.css` into modular stylesheets (`tokens.css`, `layout.css`, `chat.css`, `messages.css`, `tools.css`, `ui-controls.css`, `drawers.css`, `utilities.css`) re-imported by an aggregator `theme.css`, and split `chat.js` into focused mixins (`chatFormat.js`, `chatMessages.js`, `chatStore.js`, `chatEvents.js`, `chatHistory.js`, `chatScroll.js`) folded into the component via `Object.assign`; replace inline styles in `index.html` with utility classes and drop the `?v=N` cache-buster query strings.
- Dev dependencies: add `detect-secrets>=1.5.0` (secrets detection used by the pre-commit hooks) and sync `uv.lock`.
- `GetUrl` tool: fetched content larger than a configurable threshold (default 10,000 characters) is now written to a temporary file and returned as a pointer (`tmp_filename`) instead of inline, preventing oversized payloads from bloating the model context; created temp files are tracked and automatically removed when the janito process exits. Adds a new `threshold` parameter (pass `None`, or `-1` on the CLI, to disable the behaviour).
- `ListFiles` and `SearchText` tools: `.gitignore` patterns are now loaded from the current working directory (instead of each searched directory) and matched against paths relative to the working directory, so ignore rules apply consistently regardless of which directory is being listed or searched. Directory-only gitignore patterns (those ending with `/`) now correctly match only directories.
- `SearchText` and `SearchRegex` tools: suppress the trailing newline in search progress messages by passing `end=""` to `report_start`, so the progress line stays on a single line while results stream below it.
- Release workflow: upload only `dist/*.whl` and `dist/*.tar.gz` as release assets, excluding stray build artifacts (e.g. `default.gitignore`).
- Interactive shell: print an "Unknown command" message for unrecognized `/` commands instead of sending them to the LLM.
- Test tooling: consolidate all test modules under `tests/` (move `janito/tooling/test_path_utils.py`, `janito/test_config_dir.py` and `janito/test_general_config.py` into `tests/`, and add `tests/test_system_prompt.py`) and point `tox` (invoked by the pre-commit `run-tests` hook) at `pytest tests/`, so the full suite is executed on every commit.
- Show a 🔍 emoji in the search progress messages of the `SearchText`, `MoveEmails` and `ReadEmails` tools.
- Add contextual emojis to the progress messages of tools across file operations, Gmail, OneDrive, system commands, skills and MCP tooling (e.g. 📝 create, 🗑️ delete, 📦 move, 📖 read, 🔍 search, 🐍 Python, ⚙️ Bash/PowerShell, 🌐 fetch URL, 🔌 MCP tool, 🎓 load skill).
- Config: validate the `provider` value against the supported providers list, raising a clear error that enumerates them for unknown providers and normalizing the stored value to its canonical casing; the CLI `set` command now prints the underlying error message directly.
- CLI: whenever `--provider <name>` is used it is now validated against the supported providers (those that map to a base URL) before any command runs; unknown providers are rejected with an error enumerating the supported providers, and the value is normalized to its canonical casing.
- **Breaking:** remove the `dry_run` parameter from the `DeleteOneDriveFile` tool; the tool now always performs the deletion.
- File-search tools: extract shared `.gitignore` loading and matching helpers into a new `janito/tools/files/gitignore_utils.py` module, removing duplicated code from `find_files.py`, `list_files.py` and `search_text.py`.
- System prompt: remove the "In case of ambiguity or multiple options, ask for clarification before answering" instruction.
- `GetUrl` tool: refactor the fetch implementation to use `urllib` directly within the tool instead of spawning a subprocess that runs an inline Python script, eliminating subprocess overhead, JSON marshalling, and timeout buffering; redirect suppression is now handled by a dedicated `_NoRedirectHandler` class, and content decoding uses `errors="replace"` for resilience.
- Web settings: remove the `thinking` and `verbose` toggles from the web settings UI and the backend PATCH `/config` endpoint's mutable fields, since these are CLI-level flags that cannot be meaningfully toggled at runtime.
- Interactive shell and `/ask`: reword the request-interrupted message to "Request interrupted, previous prompt/answer removed from the conversation history." for clarity.

## [v4.12.0](https://github.com/joaopinto/janito/compare/v4.11.0...v4.12.0) - 2026-07-26

Changes since `v4.11.0` (2026-07-25).

### Added

- Add `-c` / `--config-dir` CLI option to override the default `~/.janito` config directory ([a617f82](https://github.com/joaopinto/janito/commit/a617f82)).
- Store `model` and `endpoint` settings per-provider in the config file ([0269b2f](https://github.com/joaopinto/janito/commit/0269b2f)).
- Track `git diff` after prompt processing so file changes made during a session can be reviewed (closes #7) ([4301d5d](https://github.com/joaopinto/janito/commit/4301d5d)).
- Web chat: "Jump to latest" pill with scroll-lock during streaming ([09ff448](https://github.com/joaopinto/janito/commit/09ff448)).
- Show a summary banner with the total of active and skipped tools when the shell starts (#10) ([fa9ae3a](https://github.com/joaopinto/janito/commit/fa9ae3a)).

### Changed

- **Breaking:** migrate provider configuration to a nested, provider-scoped structure and centralize config utilities ([33cd639](https://github.com/joaopinto/janito/commit/33cd639)).
- **Breaking:** replace `OPENAI_*` environment variables with local file-based config resolution ([40b21bd](https://github.com/joaopinto/janito/commit/40b21bd)).
- **Breaking:** remove the `--endpoint` CLI argument in favor of `--set endpoint=...` ([6e1cf3e](https://github.com/joaopinto/janito/commit/6e1cf3e)).
- Make provider resolution explicit and raise a clear error when no provider is configured ([41341bb](https://github.com/joaopinto/janito/commit/41341bb)).
- Make `/multi` single-use and add a web tools summary banner (closes #12) ([933dc55](https://github.com/joaopinto/janito/commit/933dc55)).
- Clarify the interrupt message to mention conversation history rollback ([e5c8b7b](https://github.com/joaopinto/janito/commit/e5c8b7b)).
- Remove git diff execution from the interactive shell (diff is now shown after prompt processing) ([b6eca0e](https://github.com/joaopinto/janito/commit/b6eca0e)).
- Add an AI-generated content disclaimer to the README ([abae470](https://github.com/joaopinto/janito/commit/abae470)).

### Fixed

- Provider-scoped config: fix integer coercion for numeric settings and repair test setup ([ca3ffb3](https://github.com/joaopinto/janito/commit/ca3ffb3)).
- Web chat: show execution time even when it is `0ms`, and improve spacing ([4236898](https://github.com/joaopinto/janito/commit/4236898)).

## [v4.11.0](https://github.com/joaopinto/janito/releases/tag/v4.11.0) - 2026-07-25

See the [release notes](https://github.com/joaopinto/janito/releases/tag/v4.11.0) for earlier changes.
