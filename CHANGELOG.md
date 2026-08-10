# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.21.0...HEAD)

Changes since `v4.21.0` (2026-08-08).

### Added

- The **AskUser tool now works in web mode**: instead of reading from stdin
  (which is not available in the web server), `BaseTool.prompt_user` checks a
  pluggable prompt handler installed by the web backend
  (`janito/tooling/prompting.py` context variable, mirroring the reporter
  pattern). The handler (`janito/web/backend/prompts.py`) registers a
  per-connection pending prompt, sends a `{"type": "prompt", "prompt_id",
  "question"}` frame to the browser and blocks the tool's worker thread until
  the answer arrives. The frontend renders a modal (root app component,
  `templates/partials/prompt_modal.html`) with the question (markdown) and an
  answer box; submitting posts `{"type": "prompt_answer", "prompt_id",
  "answer"}` back over the session's WebSocket, which the receive loop
  (`_await_cancel` in `routers/chat.py`) resolves to wake the tool thread.
  The modal works for background sessions too, cancelling a turn
  (Ctrl+C) or a disconnect resolves any pending question as an empty answer
  so the worker thread never hangs, and the CLI `input()` fallback is
  unchanged. Added `tests/test_prompting.py` (handler delegation, stripping,
  exception contract) and `tests/web/test_web_prompt_modal.py` (registry,
  `_await_cancel` resolution, full tool-thread round trip, frontend wiring).

- New `/skills` shell command lists all available skills (home + local) with
  their descriptions, mirroring the `/tools` command. Implemented in
  `janito/shell/cmds/skills.py` and registered in the shell command package,
  `/help`, command autocomplete, and the interactive-mode docs. Added
  `tests/test_shell_skills_cmd.py` covering registration, dispatch, home/local
  rendering, local-overrides-home dedup, truncation, and the empty case.

- Documentation: the docs now distinguish between the **terminal CLI/shell**
  and the **web UI** interfaces. A new page `docs/usage/cli-vs-web.md`
  compares the two feature-by-feature (starting a session, chat experience,
  commands & shortcuts, sessions & history, configuration & secrets,
  authentication & security, tools & integrations, observability &
  maintenance); `docs/usage/index.md`, `docs/usage/interactive-mode.md`,
  `docs/usage/web-ui.md` and `docs/index.md` now cross-link the two
  interfaces, and `mkdocs.yml` includes the new page in the Usage nav.

- New `scripts/provider_token_benchmark.py` developer utility: runs
  `janito -p <provider> -v --log=info "<prompt>"` for every provider with a
  configured API key (discovered via `janito --list-keys`), extracts the
  output-token usage of each run (exact per-round counts from the
  `--log=info` "Request completed" lines, falling back to the formatted
  `Out:` summary value, summed across tool rounds), writes a JSON report
  (`provider_tokens.json`) sorted by output tokens, and renders a
  dependency-free PNG bar chart (`provider_tokens.png`) sorted by tokens per
  model. Both artifacts are saved to the system temp directory by default
  (overridable with `--json` / `--png`) so they persist across runs, and
  their paths are printed to the console. Added
  `tests/test_provider_token_benchmark.py` covering the parsing, report
  building, provider discovery and the PNG renderer.

- While a prompt is pending, pressing **Enter** now cancels the in-flight request ("interrupt without rollback"): `_run_with_progress_bar()` (`janito/openai_client/completions_api.py`) polls stdin non-blockingly while the "Waiting for response from the API server..." spinner runs (`select` on POSIX, `msvcrt` on Windows, only when stdin is an interactive TTY) and, on an Enter press, sets a shared `cancel_event` that the stream consumers (`completions_stream`, `responses_stream`, `anthropic_stream`, `dashscope_stream`) honour between chunks/events, closing the HTTP stream. It then raises the new `RequestCancelled` exception. Unlike Ctrl+C (`KeyboardInterrupt`), which rolls the conversation history back to the last checkpoint, the Enter-cancel keeps the user's message in the history (`janito/shell/interactive.py` prints "Request cancelled (Enter). The prompt stays in the conversation history."), so the chat continues from where it was interrupted; `/ask` (`janito/shell/cmds/ask.py`) and single-prompt mode (`janito/cli/chat.py`) handle it too (single-prompt exits 130 like Ctrl+C). Added `tests/test_enter_cancel.py` (non-TTY guard, POSIX Enter detection via pty, progress-bar cancel/return/exception semantics, shell history preserved on Enter vs rolled back on Ctrl+C) and re-added the cancel short-circuit case to `tests/test_stream_consumers.py`.

- The Enter-cancel keeps the conversation **context** intact across all API modes: `_run_with_progress_bar()` now carries the worker's partial result on the raised `RequestCancelled` (`partial_result`), and `conversations_api._run_stream_round()` attaches the conversation state to the exception. For server-side Responses (e.g. OpenAI) the shell keeps chaining from the last *completed* response id and re-sends the cancelled message as input items (`previous_items`) on the next turn — never from the aborted response id, which the provider discards when a stream is interrupted (OpenAI answers `previous_response_id not found` for it). Stateless Responses (e.g. DeepSeek) hand back the full client-side items including the cancelled message (also covering a fresh conversation where the shell had no items yet). `janito/shell/interactive.py` consumes it so the LLM still knows the previous messages after an Enter-cancel. Completions/Anthropic/DashScope already preserved the message (their history is mutated in place).

- The web status bar now shows an "image" indicator that lights up when the
  next prompt can generate images: whenever the provider in use is
  **alibaba** (the `CreateImage` tool, Wan 2.7 Image Pro) or **openai**
  with the effective API type set to the **Responses** API (the native
  `image_generation` tool). The badge mirrors the backend's gating
  (`CreateImage.should_load` / `responses.build_call_kwargs`) and is driven
  by the same effective-provider / effective-API-type resolution the status
  bar already uses, so it updates when the provider is switched from the
  topbar combo or the API type is changed in Settings.

- The web agentic loop now supports native image generation on the
  **Responses API**: when the effective model is a mainline gpt-5 family
  model (e.g. `gpt-5.6`), the Responses runner automatically appends the
  built-in `image_generation` tool to every turn (it is a model capability,
  so it is enabled even with `--no-tools`). `image_generation_call` output
  items streamed by the API are captured by `ResponsesTurnAccumulator`,
  base64-decoded into kept temp PNG files (served by the existing
  `/api/images/` router), and surfaced to the browser as a new `image` event
  (`ImageEvent`) that the frontend renders as a content card. The saved
  paths are also persisted on the turn's assistant message (`images` key) so
  history reload rebuilds the cards. Non-gpt-5 models (e.g. `gpt-4`,
  DeepSeek) are unaffected.

- The web agentic loop now supports the same API types as the CLI clients,
  using the API type selected for the provider in use. `stream_prompt()`
  resolves the effective API type for the effective provider (`--api-type`
  first, then the provider's configured `api-type` written by the Settings
  drawer's per-provider combo, then the provider's built-in default) and
  dispatches to a per-type runner: `Completions` (the built-in Chat
  Completions path), `Responses` (`client.responses.create`, stateless
  input-items conversation model so the portable OpenAI-format session
  history is re-sent every round), `Anthropic` (native `anthropic` SDK, with
  system-prompt extraction and `tool_use`/`tool_result` conversion) and
  `DashScope` (native `dashscope` SDK, streamed off the event loop with the
  one-time multimodal/text endpoint retry). The session history stays in the
  OpenAI chat format for every API type, so frontend rendering, on-disk
  persistence and `run_tool_turn` are unchanged. The web status bar now
  shows the effective API type for the selected provider, and
  `janito --web --api-type <type>` pins it for the whole server run.

### Changed

- The CLI and web agent loops now share a single **per-API adapter layer**
  (`janito/agent/`), with two thin orchestration loops kept on top. The
  per-API call-kwargs builders, stream accumulators, history converters and
  usage normalization used to be implemented twice — once for the CLI
  (`janito/openai_client/*`) and once for the web (`janito/web/backend/agent/*`).
  They now live once:
  - `janito/agent/completions.py` — the Chat Completions accumulator
    (previously duplicated as the web `StreamAccumulator` and the CLI
    `CompletionsStreamConsumer`, which is now a thin subclass adding the
    synchronous Enter-cancel `consume` driver) and the web `build_call_kwargs`.
  - `janito/agent/responses.py` / `anthropic.py` / `dashscope.py` — the
    Responses/Anthropic/DashScope accumulators, kwargs builders and history
    conversions (moved from the web runners; the web runner modules are now
    thin shims that re-export the shared adapters and keep the async glue:
    SDK client creation + event-stream drivers).
  - `janito/agent/usage.py` — shared `normalize_usage` / `format_tokens` /
    `usage_event_from_usage`, used by the CLI usage summary
    (`client_support._display_usage`) and the web `UsageEvent` alike; the
    per-API attribute plumbing (`input_attr`/`output_attr`) is gone.
  - `janito/agent/events.py` — the agent event dataclasses, moved out of the
    web backend (the `janito.web.backend.events` path re-exports them).
  - `janito/tooling/executor.run_tool` — the shared synchronous tool-execution
    core used by the CLI `ToolExecutor` and by the web loop (which runs it in
    a thread, capturing `report_*` output as `ToolProgressEvent`s). The web
    `agent/tooling.py` no longer re-implements MCP routing / usage / used-file
    / changes tracking (`is_mcp_tool` is imported from the executor).
  Behaviour is unchanged for both loops; all existing import paths (web
  runner modules, `janito.web.backend.events`, the CLI stream consumers and
  `format_tokens`) are preserved via re-export shims, so no test churn was
  required. ~1,500 lines of duplicated adapter code were removed.

- The interactive shell command `/btw` (individual question with a fresh chat
  history) has been renamed back to `/ask`: the handler now lives in
  `janito/shell/cmds/ask.py` (class `AskCmdHandler`, registered as `/ask`),
  and the package import in `janito/shell/cmds/__init__.py` was updated
  accordingly. Updated `tests/test_shell_completer.py`, the comment in
  `janito/shell/interactive.py` and `docs/usage/cli-vs-web.md`.

- Docs: the web UI installation section (`docs/usage/web-ui.md`) now shows
  the `uv tool install janito[web]` alternative next to
  `pip install janito[web]`, and the frontend section no longer refers to
  pip specifically when describing the `[web]` extra.

- Docs: renamed `docs/cli_lanscape.md` to `docs/cli_landscape.md` (fixing
  the misspelling) and expanded the CLI landscape table with an **OSS**
  column and system-prompt sizes for janito, Opencode, Claude Code, Pi and
  Codex.

- The interactive shell command `/show_config` (displays the current
  configuration: provider, API type, base URL, masked API key, max output
  tokens, reasoning level and thinking mode) has been renamed to `/status`:
  the handler now lives in `janito/shell/cmds/status.py` (class
  `StatusCmdHandler`, registered as `/status`), and the package import in
  `janito/shell/cmds/__init__.py` was updated accordingly. Updated
  `tests/test_shell_config_cmd.py`, `tests/test_shell_completer.py` and the
  docstring example in `janito/shell/cmds/base.py`.

- The interactive shell command `/ask` (individual question with a fresh chat
  history) has been renamed to `/btw`: the handler now lives in
  `janito/shell/cmds/btw.py` (class `BtwCmdHandler`, registered as `/btw`),
  and the package import in `janito/shell/cmds/__init__.py` was updated
  accordingly. Updated `tests/test_shell_completer.py` and the comment in
  `janito/shell/interactive.py`.

- Unified diffs shown in the CLI (both the `report_diff` output emitted by
  `ReplaceTextInFile` and the `/changes` command's `ReplaceTextInFile`
  entries) are now rendered with a dedicated Pygments style
  (`janito.tooling.reporter.DiffTheme`) that gives removed lines (`-`) a red
  background and added lines (`+`) a green background, so the hunks stand out
  at a glance (the text stays plain white on both, and context lines keep a
  neutral dark background). The `/changes`
  command now always renders these diffs with the Pygments "diff" lexer
  (previously it guessed the lexer from the file path, which did not mark the
  `-`/`+` lines). Added `tests/test_report_diff.py` coverage for the theme's
  token styles and the emitted ANSI background codes, and a
  `tests/test_changes.py` case asserting the diff backgrounds in the
  `/changes` output.

- The web chat page (previously a single ~900-line
  `janito/web/frontend/index.html`) is now composed server-side with Jinja2:
  the shell lives in `janito/web/backend/templates/base.html` and each UI
  section (sidebar, topbar, chat area, message/part rendering, input area,
  status bar, tools dialog, settings drawer, MCP drawer, toast) in a partial
  under `templates/partials/`. `janito/web/backend/templating.py` owns the
  Jinja2 environment (shared by the app and the contract tests), and
  `app.py` renders `base.html` per request — preserving the existing
  behaviour: `no-store`, mtime-based cache-busting of local `/js/` + `/css/`
  assets, and the `window.__JANITO_TOKEN__` injection (now a template
  context value JSON-escaped via `tojson`). The rendered page is
  byte-identical to the previous static file. `jinja2` was added to the
  `web` optional dependency group, and the frontend contract tests now
  render the templates through `tests/web/_frontend.py:render_index_html()`
  instead of reading `frontend/index.html`.

- The `moonshot` provider now declares its supported reasoning levels
  (`low`/`high`/`max`, with `max` as the built-in default, per the
  Moonshot/Kimi API reference) in `janito/provider_data.py` `PROVIDER_INFO`,
  so `get_default_reasoning_level_from_provider("moonshot")`,
  `get_supported_reasoning_levels_from_provider("moonshot")` and the web
  `/providers` endpoint expose them. The Moonshot section of
  `docs/configuration/providers.md` gained a "Reasoning Level" subsection
  documenting the levels and the resolution order;
  `tests/test_provider_config.py` now asserts the moonshot levels.

- The web topbar's provider switcher combo now shares the exact styling of
  the Settings drawer's provider combobox (same bordered
  `.form-group select` look: background, border, radius, padding and font
  size), instead of the previous transparent select inside a pill wrapper.
  The `<select>` itself now carries the border/background and the native
  dropdown arrow, so the two combos render identically (the custom caret
  span was removed).

- Docs: the Supported Providers table in `docs/configuration/providers.md`
  no longer has a **Type** column (the `Standard` / `Custom` /
  `Third-party` grouping was not referenced anywhere else in the docs),
  and OpenAI is no longer marked as the default provider; the table now
  lists `Provider` and `Description` only.

### Fixed

- MCP stdio commands configured as a single string (e.g. by `/mcp add`
  `myserver stdio python -m mcp.server`) now work: `StdioTransport` splits
  the command with `shlex.split()` before spawning the subprocess, so
  `subprocess.Popen` receives proper argv instead of a single
  space-joined string (which previously failed with `No such file or
  directory`). Pre-split argv lists are still accepted as-is.

- `MCPManager.get_all_tools()` no longer drops a service's tools when the
  service had to be reconnected: the reconnect path previously `continue`d
  past the `tools/list` call, so a restarted server's tools vanished from
  the (cached) tool list until the manager was rebuilt.

- The HTTP transport now clears its connected flag when a request or
  notification fails, so `MCPManager` (and other callers) can detect a dead
  remote server and attempt a reconnect instead of treating the stale
  flag as live and silently returning an empty tool list.

- `MCPManager.call_tool()` caches each service's tool names (populated by
  `get_all_tools()`, invalidated on connect/unload) instead of re-listing
  tools on every invocation; a failed live lookup no longer aborts the call
  but is treated as "tool not found".

- MCP image results no longer dump raw base64 into the conversation
  history; `_process_tool_result` reports `[Image: <mime>, <N> bytes]`
  instead.

- `/mcp list`, `/mcp` help and `janito --list-mcp` now display the config
  file path via `get_mcp_config_path()` so it honours the `-c` /
  `--config-dir` override instead of the import-time constant.

- Added `tests/test_mcp_client.py` covering both transports end to end
  (stdio subprocess and HTTP/SSE), the stdio command-splitting fix, the
  manager reconnect fix, and HTTP disconnection detection.

### Removed

- Removed the Enter-to-cancel functionality in interactive mode: pressing
  `Enter` while a prompt was pending ("Waiting for response from the API
  server...") used to interrupt the in-flight request (letting the user
  extend the message with extra lines). The shell no longer polls stdin for
  an `Enter` press while waiting for the API, the `RequestCancelled`
  exception and its handlers were dropped, and pressing `Enter` is ignored
  until the response completes. Cancelling a pending request is still
  possible with `Ctrl+C` (which rolls the last prompt/answer back out of the
  history).

## [v4.21.0](https://github.com/joaopinto/janito/compare/v4.20.0...v4.21.0) - 2026-08-08

Changes since `v4.20.0` (2026-08-07).

### Added

- `exclude` parameter on `SearchText` and `SearchRegex` to skip files and
  directories via space-separated glob patterns (e.g.
  `"*/node_modules/* */__pycache__/*"`). `FindFiles` now also prunes excluded
  directories during the walk instead of only filtering entries, so the three
  search tools behave consistently. Excluded directories are not walked into,
  single-file roots are matched against their basename, and the parameter works
  in `count_only` mode too. The shared glob matcher was extracted into
  `janito/tools/files/glob_utils.py`.
- `HeadlessBrowse` in the `net` toolset: renders a URL with headless Google
  Chrome and returns the page's DOM, so JavaScript-generated content is
  captured (unlike the plain-HTTP `GetUrl`). The tool is only loaded when a
  Chrome/Chromium-based browser binary is found (`should_load`), launches
  Chrome with an isolated profile and a virtual-time budget (`wait_ms`) for JS,
  and mirrors `GetUrl`'s truncation and oversized-content-to-temp-file
  behaviour. Falls back from `--headless=new` to the legacy `--headless` flag
  for older Chromium builds. Closes #43.
- `-l` / `--local` CLI switch for project-local configuration. When used,
  `--set`, `--set-api-key`, `--set-secret` (and the other config/auth/secret
  commands) store their files in `./.janito` (the current working directory)
  instead of `~/.janito`. Reads resolve local values first and fall back to
  the global directory (`~/.janito` or the `-c` / `--config-dir` override),
  and `--list-keys` / `--list-secrets` show both the local and the global
  entries. `janito/config_dir.py` gained a resolution chain
  (`get_config_dirs` / `get_config_file_paths`) used by `general_config`,
  `auth_config` and `secrets_config`; writes always target the primary file
  only, so a local `--set` never copies global entries into `./.janito`.
  Closes #45.

### Changed

- The `deepseek` provider now declares its supported reasoning levels
  (`low`/`high`/`max`, per the DeepSeek API reference) in
  `janito/provider_data.py` `PROVIDER_INFO`, so
  `get_supported_reasoning_levels_from_provider("deepseek")` and the web
  `/providers` endpoint expose them (previously only `alibaba` declared
  levels).  The DeepSeek section of `docs/configuration/providers.md` gained
  a "Reasoning Level" subsection documenting the levels, the `medium`/`xhigh`
  compatibility mappings and the `deepseek-v4-pro` `high`/`max` limitation;
  `tests/test_provider_config.py` now asserts the deepseek levels.
- Documentation: the README, `docs/index.md` and the providers guide
  (`docs/configuration/providers.md`) now state that janito supports **both**
  OpenAI-compatible APIs (the `Responses`/`Completions` API types) and native
  provider SDKs (the `Anthropic` and `DashScope` API types).
- Extracted the system-prompt / toolset selection that was duplicated
  between ``cli/chat.py`` and ``WebServerConfig`` into a shared
  ``SessionSetup`` class (`janito/cli/session_setup.py`).  Both entry points
  now delegate to it: ``cli/chat.py``'s ``_resolve_system_prompt`` /
  ``_build_single_prompt_context`` / ``_enable_requested_toolsets`` and
  ``WebServerConfig.get_effective_system_prompt`` / ``apply_toolsets`` (the
  web ``apply_toolsets`` additionally enables the web-only ``"janitoweb"``
  toolset via the new ``extra`` parameter).  ``chat.py`` keeps
  ``get_system_prompt_with_skills`` as a documented backward-compat
  re-export (``test_version_banner.py`` patches
  ``chat_mod.get_system_prompt_with_skills``).  New tests:
  `tests/test_session_setup.py` (including a CLI<->web parity check).

- Introduced `ToolsRegistry`
  (`janito/tooling/tools_registry.py`) as a class-based API over the
  module-level registry state (lazy discovery, toolset loading, skills
  enable/disable, tool/schema/permission lookups).  The registry state
  intentionally stays at module level (`AVAILABLE_TOOLS`,
  `_tools_initialized`, ...) because the tests monkeypatch those names
  directly to inject stub tools without triggering the slow filesystem
  discovery; the module-level functions are now thin delegators to a
  module-level singleton.  New tests: `tests/test_tools_registry.py`.
- Deleted `janito/tooling/mcp_registry.py`: it was dead code (no importers
  anywhere in `janito/` or `tests/`, not re-exported from the package).  The
  live MCP-tool routing lives in `ToolExecutor` (via `MCPManager`), so the
  legacy parallel registry served no purpose.
- Introduced tracker classes for the three best-effort tracking side
  features, each keeping its module-level functions as thin delegators to a
  module-level singleton:
  - `ChangesTracker` (`janito/tooling/changes.py`) - records and renders the
    file-changing tool executions (the `/changes` command).
  - `UsedFilesTracker` (`janito/tooling/used_files.py`) - tracks the READ /
    WRITE file paths per prompt; instances carry their own state, which is
    useful for the web backend's concurrent tools.
  - `ToolUsageStore` (`janito/tooling/tools_usage.py`) - SQLite-backed
    per-tool usage counters; accepts an explicit `db_path` for isolation.
  - New tests: `tests/test_trackers.py`.
- `janito/tooling/config_dir.py` (`ConfigDirManager`) was intentionally left
  as module functions: the module is small, deliberately dependency-free, and
  its two globals are monkeypatched directly by `test_config_dir.py` /
  `test_local_config.py`, so a class would add ceremony without
  encapsulation.

- Introduced `*StreamConsumer` classes as the real implementation of the
  four stream-assembly modules, removing the ``state``-dict plumbing
  between handlers: `ResponsesStreamConsumer`
  (`janito/openai_client/responses_stream.py`), `CompletionsStreamConsumer`
  (`completions_stream.py`), `AnthropicStreamConsumer`
  (`anthropic_stream.py`) and `DashScopeStreamConsumer`
  (`dashscope_stream.py`).  Each consumer holds the assembled response parts
  (content / reasoning / tool calls / usage / response id) as instance
  attributes, exposes `consume()` plus `handle_*` methods, and is driven by
  the module-level `_consume_*` / `_stream_response` functions, which remain
  as thin delegators so existing callers and test monkeypatches are
  unaffected.  The re-exported `_handle_*`/`_consume_*` helpers keep their
  exact signatures via small legacy ``state``-dict bridges (used by no code
  path; kept for backward compatibility).  New tests:
  `tests/test_stream_consumers.py`.

- Introduced a shared `Client` base class
  (`janito/openai_client/base_client.py`) implementing the duplicated
  ~300-line agent-loop pipeline (reset tracking -> resolve runtime config ->
  create SDK client -> load MCP tools -> build the ToolExecutor -> resolve
  model settings -> loop *stream / display / tool calls / finalize*) as a
  template method (`Client.send`).  The four API clients now subclass it:
  `CompletionsClient` (`completions_api`), `ResponsesClient`
  (`conversations_api`), `AnthropicClient` (`anthropic_api`) and
  `DashScopeClient` (`dashscope_api`); the module-level `send_prompt`
  functions remain as thin wrappers with their exact signatures, so the
  interactive shell, `cli/chat.py` and the tests are unaffected.
  Each subclass implements its hooks as forwarders to its own module's
  globals (`resolve_runtime_config`, `_run_with_progress_bar`, `OpenAI`,
  `ToolExecutor`, `get_all_tool_schemas`, ...), so the existing test
  monkeypatches keep working.  Conversation state differs per client: the
  Responses client threads a small state dict (server-side `response_id` vs
  stateless `input_items` + `message_count`), while the stateless clients
  keep the caller-owned messages list with the historical "is not None"
  empty-list semantics.  New tests: `tests/test_clients.py`.

- Extracted the duplicated JSON-file store pattern (path resolution,
  local-over-global merge, `0600` permissions, get/set/delete/list) into a
  new `janito/json_store.py` module: `auth_config`, `secrets_config` and
  `mcp_config` now delegate to `AuthConfigStore` / `SecretsConfigStore` /
  `McpConfigStore` subclasses of a shared `JsonFileStore` base. Every
  module-level function is preserved as a thin delegator to a module-level
  singleton, so existing imports keep working. One intentional
  normalization: `load_auth_config()` now tolerates a corrupted `auth.json`
  (logs and returns `{}`) instead of propagating `json.JSONDecodeError`,
  matching the existing `secrets_config` behaviour.
- Introduced class-based APIs for the configuration modules while keeping
  every module-level function as a backward-compatible delegator (same
  pattern as the earlier module splits):
  - `ProviderConfigLoader` (`janito/config_loaders.py`) centralizes the six
    per-provider loaders (model, max-output-tokens with its legacy key
    chain, reasoning-level, api-type, responses-in-server, endpoint). Its
    helpers are imported lazily so the module is importable in either
    direction of the `general_config` re-export (removes a latent circular
    import when `config_loaders` is imported first).
  - `Provider` / `ProviderRegistry` (`janito/provider_config.py`) provide
    typed accessors over `PROVIDER_INFO`. The registry holds a live
    reference (never a copy) and constructs providers on demand, so runtime
    mutations of `PROVIDER_INFO` (e.g. injected test providers) are
    reflected in every lookup; the whitespace distinction between
    `get_provider_info` (no strip) and `canonical_provider_name` (strips) is
    preserved. Directly constructing `Provider("unknown")` now raises
    `ValueError` instead of `KeyError`.
  - `ConfigStore` (`janito/general_config.py`) centralizes the
    load/save/get/set/unset primitives and the provider-scoped key handling
    previously duplicated between `set_config_value` and
    `unset_config_value`.
  - New tests: `tests/test_json_store.py`, `tests/test_config_loaders.py`,
    `tests/test_provider.py`, `tests/test_config_store.py`.

- The code search index no longer stores a per-file SHA-1 content hash.
  `CodeSearch.Update()` now detects changed files by comparing the file's
  last modified time (`mtime`) against the indexed one, avoiding a full read
  of every file on each refresh. Indexes created with the previous schema
  (v1, with a `sha1` column) are automatically rebuilt on the next
  `Create()`/`Update()`.
- `CodeSearch.Find()` (and the `CodeSearch` tool) now performs **whole-word
  matching** and returns **line results** instead of bare file paths.
  Keywords must appear as whole words (`foo` no longer matches `foobar` or
  `foo_bar`) on a single line; the trigram index still narrows the candidate
  files, which are then scanned line by line (files in the index that no
  longer exist on disk are skipped). For `"and"` every keyword must be on
  the same line, for `"or"` any keyword suffices. `Find()` yields
  `CodeSearchMatch(path, lineno, content)` objects, and the tool returns
  `matches` formatted as `path:lineno: content` (the same format as the
  other search tools) plus `total_matches`. This breaks the previous
  filenames-only return contract on purpose; no backwards compatibility is
  kept.
- Enabled ruff's mccabe complexity check (`C901`) in `[tool.ruff.lint]` with
  `max-complexity = 10` in `[tool.ruff.lint.mccabe]`. Closes #44.
- Reduced the cyclomatic complexity of the remaining hot functions so the
  whole codebase passes `ruff check` with `max-complexity = 10` (was 46 `C901`
  violations). All refactors are behaviour-preserving:
  - The CLI entry point (`janito/__main__.py`) was split into a dispatch
    table plus small setup/batch-config helpers; the `--config` wizard
    (`janito/cli/handlers/config.py`), `--info` resolution and the
    interactive shell loop were decomposed into focused helpers.
  - The `SearchText` and `SearchRegex` tools now share their directory
    walking / ignore / exclude / aggregation logic via a new common base
    module `janito/tools/files/search_base.py`; each tool keeps only its
    per-line matcher, `run()` and CLI harness (each file roughly halved).
  - The file tools (`ListFiles`, `MoveFile`, `RemoveDirectory`,
    `ReadMultipleFiles`) extract their walk/validate/move logic into small
    private helpers.
  - The Gmail tools reuse shared credential fetching, IMAP connection and
    search-criteria helpers in `janito/tools/gmail/imap_utils.py`; the
    OneDrive tools (`base_client`, `list_files`, `read_file`,
    `download_file`, `__main__`) extract request/format helpers.
  - `CreateImage`, `WebSearch`, `CodeSearch.Find`, the web agent's
    `stream_prompt`/`StreamAccumulator`, the WebSocket loop and
    `patch_config` were decomposed into small helpers, and
    `scripts/promote_changelog.py` splits out version/date/section
    resolution.
- Split the remaining production Python files over 600 lines into focused
  modules. Every refactor is behaviour-preserving (no public API changed;
  moved helpers are re-exported from their original modules so existing
  imports and test monkeypatches keep working):
  - The four API clients (`janito/openai_client/completions_api.py`,
    `conversations_api.py`, `anthropic_api.py` and `janito/dashscope_api.py`)
    now share their duplicated support code (token formatting, MCP loading,
    Rich console output, auth-error explainer) from
    `janito/openai_client/client_support.py`, and each client's stream
    consumption moved to its own module (`completions_stream.py`,
    `responses_stream.py`, `anthropic_stream.py`, `dashscope_stream.py`);
    the Responses conversation-state setup moved to
    `responses_state.py`. Each client file shrank below 600 lines.
  - `janito/general_config.py` now only holds the core config storage and
    key-resolution primitives; the per-provider loaders moved to
    `janito/config_loaders.py` and the `--set`/`--get`/`--unset` CLI helpers
    plus `ProviderRequiredError` moved to `janito/config_cli.py`.
  - `janito/provider_config.py` keeps the accessor functions while the
    static provider registry moved to `janito/provider_data.py`.
  - `janito/tools/files/find_files.py` delegates its pure filter helpers to
    `janito/tools/files/find_files_utils.py` and its standalone CLI harness
    to `janito/tools/files/find_files_cli.py`.
  - `janito/codesearch/code_search.py` delegates candidate selection and
    line scanning (plus `MATCH`/`CodeSearchMatch`) to
    `janito/codesearch/candidates.py`.
  - The web config router (`janito/web/backend/routers/config.py`) moved its
    per-provider `PATCH /api/config` helpers to
    `janito/web/backend/routers/config_helpers.py`.

- Updated the built-in `deepseek` provider info with its Anthropic-compatible
  base URL (`https://api.deepseek.com/anthropic`). The provider now declares
  the native `Anthropic` SDK API type (in addition to the OpenAI-compatible
  `Responses` / `Completions` types) and an `endpoint_by_api_type` map: the
  OpenAI-compatible types keep using `https://api.deepseek.com` while the
  `Anthropic` type uses `https://api.deepseek.com/anthropic`, so the native
  Anthropic SDK client can talk to DeepSeek with `--set api-type=Anthropic`
  (requires the optional `anthropic` package).
