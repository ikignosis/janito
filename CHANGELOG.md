# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.20.0...HEAD)

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
