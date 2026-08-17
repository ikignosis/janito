# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.25.0...HEAD)

Changes since `v4.25.0` (2026-08-15).

### Added

- `--install-plugin <github_url>` downloads a GitHub repository's `master`
  zip archive and extracts it to `~/.janito/plugins/<repo-name>` (honoring
  `-c/--config-dir`). Plugins installed there are **autoloaded** on every
  janito run via the new `plugin_manager.load_installed_plugins()`.
  `--no-plugins` disables the autoload (plugins explicitly loaded with
  `--plugin DIR` are still loaded). Plugin tool registration is no longer
  gated by `--no-tools` — `--no-tools` only disables built-in tools, so
  plugin tools stay available unless `--no-plugins` is passed.
  (`janito/cli/parser.py`, `janito/cli/handlers/plugins.py`,
  `janito/cli/handlers/__init__.py`, `janito/__main__.py`,
  `janito/plugin_manager.py`, `janito/tooling/tools_registry.py`,
  `janito/web/backend/config.py`, `docs/PLUGINS.md`,
  `docs/reference/cli-options.md`, `docs/usage/cli-vs-web.md`,
  `docs/usage/web-ui.md`, `ARCHITECTURE.md`,
  `tests/test_plugin_manager.py`, `tests/test_no_tools.py`,
  `tests/test_tools_registry.py`)

- Added `../plugins/janito-codesearch-plugin/README.md` (the sibling repo
  that now hosts the codesearch plugin) describing the plugin's capabilities:
  the trigram-based `CodeSearch` tool (whole-word AND/OR matching,
  `path:lineno: content` results), the `/codesearch update | recreate` shell
  command, automatic index creation on plugin load and auto-refresh with the
  1-day TTL, `.gitignore`/`.janitoignore` handling, what gets indexed, and
  the plugin structure. (`../plugins/janito-codesearch-plugin/README.md`)

- The codesearch plugin's Python package now lives at the **root** of the
  sibling `../plugins/janito-codesearch-plugin/` repo (the old
  `codesearch/` subdirectory is gone), so it loads with
  `janito --plugin ../plugins/janito-codesearch-plugin` (no trailing
  `/codesearch`). CLI help, plugin docs and the plugin end-to-end tests now
  reference the new path. (`janito/cli/parser.py`,
  `janito/plugin_manager.py`, `docs/PLUGINS.md`,
  `docs/tools/codesearch.md`, `docs/usage/cli-vs-web.md`,
  `ARCHITECTURE.md`, `tests/test_plugin_manager.py`)

- Every built-in model entry now declares its **default API type** via the
  new `default_api_type` model-config field (the value is the model's first
  `supported_api_types` entry, e.g. `"Responses"` for OpenAI's
  `gpt-5.6-luna` and `"Completions"` for Alibaba's `qwen3.8-max`).
  `ModelConfig.default_api_type()` / `Provider.default_api_type()` /
  `get_default_api_type_from_provider()` now resolve the built-in default
  from that field instead of taking the first `supported_api_types` entry,
  and the web status bar / Settings drawer resolve the effective API type
  from `default_api_type` (dropping the client-side first-supported
  fallback).  The effective API type can still be overridden per
  provider/model with `--set api-type=...` or per-call with `--api-type`.
  (`janito/providers/*/config.py`,
  `janito/providers/template/config.py`, `janito/providers/__init__.py`,
  `janito/provider_models.py`, `janito/provider_accessors.py`,
  `janito/general_config.py`, `janito/web/frontend/js/statusBar.js`,
  `janito/web/frontend/js/settings.js`, `docs/configuration/providers.md`,
  `ARCHITECTURE.md`, `tests/test_general_config.py`,
  `tests/web/test_web_settings_advanced.py`)

- Alibaba's `qwen3.8-max` declares its built-in (native) tools
  (`code_interpreter`, `web_search`, `web_extractor`) **per API type** via
  the new `tools_by_api_type` model-config field: they are enabled on the
  Responses API only.  These are *not* function tools -- each `type` is a
  model capability enabled through request-body flags on the API call: the
  OpenAI-compatible Chat Completions API receives `extra_body`
  `{"enable_code_interpreter": true, "enable_thinking": true, "enable_search":
  true}` (code_interpreter only supports calls in thinking mode, so it also
  forces `enable_thinking` on), the Responses API receives the entries in its
  `tools` array, and the native DashScope API receives the
  `enable_code_interpreter` / `enable_search` kwargs.  The tools are
  disabled on the Completions API (and DashScope) because the qwen3.8-max
  deployment rejects `code_interpreter` there with `400 InternalError.Algo.
  InvalidParameter: The current model does not support the code_interpreter
  tool.`; the plain `tools` config default still applies to every API type
  not listed in `tools_by_api_type`.  When a model declares built-in tools
  for an API type they are always enabled -- even with `no_tools` / an empty
  function-tools list -- mirroring the Responses `image_generation` tool:
  the CLI Responses client resolves them per model (via
  `get_default_tools_from_provider(provider, model, api_type="Responses")`)
  and merges them into the `tools` array after the converted function-tool
  schemas, matching the web agent.
  New accessors `get_default_tools_from_provider(provider, model,
  api_type)` / `Provider.tools(model, api_type)` / `ModelConfig.tools(
  api_type)` and the `builtin_tools_enable_flags` /
  `apply_builtin_tools_to_extra_body` helpers resolve and send them; the web
  agent resolves them per API type via the new
  `WebServerConfig.effective_tools_for(api_type)` method, and
  `--show-providers` surfaces them per model annotated with the API type.
  (`janito/providers/alibaba/config.py`, `janito/providers/template/config.py`,
  `janito/providers/__init__.py`, `janito/provider_models.py`,
  `janito/provider_accessors.py`, `janito/web/backend/config.py`,
  `janito/agent/completions.py`, `janito/agent/responses.py`,
  `janito/agent/dashscope.py`, `janito/openai_client/completions_helpers.py`,
  `janito/openai_client/completions_api.py`, `janito/openai_client/responses_state.py`,
  `janito/openai_client/responses_stream.py`, `janito/dashscope_helpers.py`,
  `janito/dashscope_api.py`, `janito/cli/handlers/providers.py`,
  `tests/test_provider_config.py`, `tests/test_provider.py`,
  `tests/test_reasoning_level.py`, `tests/test_show_providers.py`,
  `tests/test_dashscope_api.py`, `tests/web/test_web_api_types.py`,
  `tests/web/test_web_api_types_responses.py`,
  `tests/web/test_web_api_types_dashscope.py`, `docs/configuration/providers.md`,
  `docs/reference/cli-options.md`)
- New interactive-shell `/model` command: `/model` (no argument) shows the
  current model and the models available from the current provider;
  `/model <name>` switches the session's model at runtime (updates the
  prompt/toolbar display and rebinds the send function via the new
  `model_override` parameter of `_make_send_factory`) without changing the
  configured default `model` in config.json (use `janito --set model=<name>`
  to persist).  Like `--model`, the name is open-ended (any name is passed
  to the provider's API; a name matching an available model is canonicalized
  to its casing).  The shell's argument autocompletion (`/model <name>`)
  suggests the models available from the current provider (its built-in
  `models` registry plus configured per-model entries in config.json).
  Switching the model clears the LLM conversation history (system prompt
  preserved); a `/provider` switch clears any session model override.
  (`janito/shell/cmds/model.py`, `janito/shell/cmds/__init__.py`,
  `janito/shell/cmds/provider.py`, `janito/shell/interactive.py`,
  `janito/shell/session.py`, `janito/cli/chat.py`,
  `tests/test_shell_model_cmd.py`, `tests/test_shell_completer.py`)

### Changed

- The `## Project-Specific Instructions` header is no longer prepended to the
  `AGENTS.md` content in the system prompt; the section text is now preceded
  by a single `\n` separator and followed by a trailing `\n`.  The `agents.md`
  section label used by `/prompt` and `--show-system-prompt` is unchanged.
  (`janito/system_prompt.py`, `tests/test_system_prompt.py`)
- Plugin `SYSTEM_PROMPT` text is now appended to the system prompt as-is,
  without the `## Plugin: <name>` header; a single `\n` separator is added
  before the plugin text to split the context.  The `plugins:<name>` section
  label used by `/prompt` and `--show-system-prompt` is unchanged.
  (`janito/system_prompt.py`, `tests/test_plugin_manager.py`)
- `/prompt` and `--show-system-prompt` now display each section with
  `rstrip()` instead of `strip()`, preserving the leading whitespace (e.g.
  the blank-line separator before plugin sections) in the table rows.
  (`janito/shell/cmds/prompt.py`, `janito/cli/handlers/info.py`,
  `tests/test_shell_prompt_cmd.py`)
- `janito.plugin_manager.load_plugin()` now prints `Loading plugin <name>`
  (the plugin's directory name) before loading each plugin, so startup shows
  which plugins are being loaded. (`janito/plugin_manager.py`,
  `tests/test_plugin_manager.py`)
- Repository moved from the `ikignosis` GitHub org to `joaompinto`; updated
  the git remote and all URLs across `README.md`, `README_DEV.md`,
  `RELEASE.md`, `mkdocs.yml`, `pyproject.toml`, the docs and the changelog
  (repo, raw content and GitHub Pages links).
- Added `get_provider_cost(provider, model, input, output, cached, now=None)` in
  `janito/provider_accessors.py`: resolves a provider (case-insensitive,
  variant-aware) and delegates to its `cost.py` module's `get_cost`
  (e.g. `janito.providers.deepseek.cost`); falls back to `"N/A"` when the
  provider is unknown or ships no cost module.  The optional `now` request
  time is forwarded to `get_cost` (when it accepts it) so time-aware rate
  cards (e.g. DeepSeek peak/off-peak) can be estimated deterministically.
  (`janito/provider_accessors.py`, `tests/test_provider.py`)
- Added `janito/providers/deepseek/cost.py` with a `get_cost(model, input,
  output, cached, now=None)` helper that estimates the monetary cost of a
  request from the official per-1M-token rates (verified 2026-08-16 at
  https://api-docs.deepseek.com/quick_start/pricing) for `deepseek-v4-flash`
  ($0.22 / $0.007 cache hit / $0.66 output) and `deepseek-v4-pro`
  ($0.66 / $0.022 cache hit / $1.98 output), billing cached input tokens at
  the automatic cache-hit rate and formatting the result as `NN.DDDDDD$`
  followed by the applied rate band, e.g. `"0.880000$ (off-peak)"`; unknown
  models fall back to `"N/A"`.  Peak-hour requests (01:00-04:00 and 06:00-10:00
  UTC, where off-peak rates are half of the peak rates) are billed at exactly
  double the off-peak rates and annotated `(peak)`; pass `now` to pick the
  rate band, otherwise the current UTC time is used.
  (`janito/providers/deepseek/cost.py`, `janito/provider_accessors.py`,
  `tests/test_provider.py`, `tests/test_input_tokens_info.py`)
- Added `deepseek-v4-pro` as a built-in supported model in the `deepseek`
  provider config (`janito/providers/deepseek/config.py`): same
  `supported_api_types` (Responses / Completions / Anthropic), 1M input / 384k
  output limits and default thinking as `deepseek-v4-flash`, with
  `supported_reasoning_levels` restricted to `high`/`max` (per the DeepSeek
  API reference, `low` maps to `high` and `xhigh` to `max` for this model).
  (`janito/providers/deepseek/config.py`, `tests/test_shell_model_cmd.py`)
- Added `janito/providers/alibaba/cost.py` with a `get_cost(model, input,
  output, cached)` helper that estimates the monetary cost of a request from
  the per-1M-token rates for `qwen3.8-max` ($2 / $0.25 implicit cache hit /
  $6 output), billing cached input tokens at the implicit cache-hit rate and
  formatting the result as `NN.DDDDDD$` (e.g. `"8.000000$"`); unknown models
  fall back to `"N/A"`.  There is no peak-hour surcharge.  The module
  docstring documents the rates source (https://www.qwencloud.com/models/qwen3.8-max,
  verified 2026-08-15) and points at the official rate card
  (https://www.qwencloud.com/pricing/token-plan).
  (`janito/providers/alibaba/cost.py`, `tests/test_provider.py`)
- The token-usage summary line printed at the end of each turn now computes
  its `Cost: <cost>` part through
  `get_provider_cost(provider, model, input, output, cached)` instead of a
  never-passed `cost` argument: the provider/model are threaded from
  `Client.send()` down to `_display_usage`, cached input tokens are billed
  at the provider's cache-hit rate, and it falls back to `N/A` when the
  provider/model is unknown or ships no cost module (e.g. non-DeepSeek
  providers). (`janito/openai_client/client_support.py`,
  `janito/openai_client/base_client.py`,
  `janito/openai_client/completions_api.py`,
  `janito/openai_client/conversations_api.py`,
  `janito/openai_client/anthropic_api.py`,
  `janito/openai_client/completions_helpers.py`,
  `janito/openai_client/responses_helpers.py`,
  `janito/dashscope_api.py`, `janito/dashscope_helpers.py`,
  `scripts/provider_token_benchmark.py`, `tests/test_provider_token_benchmark.py`)
- Added `janito/providers/template/config.py`: the documentation template
  for writing a new provider's config entry, commenting every possible
  CONFIG option (provider-level `default_model` / `endpoint` /
  `endpoint_by_api_type`, and model-level `supported_api_types` /
  `responses_in_server` / `max_input_tokens` / `max_output_tokens` /
  `reasoning_level` / `supported_reasoning_levels` / `thinking`). It is not
  a real provider (never registered in `_PROVIDER_CONFIGS`). The per-provider
  `config.py` docstrings dropped their duplicated entry-schema descriptions
  and now point to the template for details (as does the
  `janito/providers/__init__.py` package docstring and `ARCHITECTURE.md`).
  (`janito/providers/template/config.py`,
  `janito/providers/template/__init__.py`, `janito/providers/*/config.py`,
  `janito/providers/__init__.py`, `ARCHITECTURE.md`)
- The module-level `PROVIDER_INFO` dict was removed: code now reads provider
  configs through `get_provider_config(provider, model=None)` (renamed from
  `get_provider_info`) instead of indexing the registry directly, and lists
  providers via `list_supported_providers()`. The backing registry is now
  internal (`janito.providers._PROVIDER_CONFIGS`).
  (`janito/providers/__init__.py`, `janito/provider_accessors.py`,
  `janito/provider_registry.py`, `janito/provider_models.py`,
  `janito/provider_validation.py`,
  `janito/web/backend/routers/config.py`,
  `janito/web/backend/routers/config_helpers.py`,
  `janito/dashscope_helpers.py`,
  `janito/openai_client/completions_helpers.py`,
  `janito/openai_client/responses_helpers.py`, `tests/test_provider.py`,
  `tests/test_provider_config.py`, `tests/test_show_providers.py`,
  `tests/test_shell_provider_cmd.py`, `ARCHITECTURE.md`,
  `docs/configuration/variants.md`)
- The static `PROVIDER_INFO` registry was split into one `config.py` module
  per provider under `janito/providers/<name>/` (each exporting that
  provider's `PROVIDER_CONFIG` entry); the package `__init__.py` assembles
  them into the internal `_PROVIDER_CONFIGS` dict, keeps the
  `REQUIRES_BY_API_TYPE` optional-package map and the `CUSTOM_ENDPOINT`
  marker, and exposes `get_provider_config(provider, model=None)` — with
  `model` given it returns that model's config *within* the provider.
  `janito.provider_data` was removed and all its consumers now read from
  `janito.providers` (the accessors' `get_provider_config` also accepts the
  new `model` argument).
  (`janito/providers/*`, `janito/provider_accessors.py`,
  `janito/provider_registry.py`, `janito/provider_models.py`,
  `janito/provider_validation.py`, `janito/config_variants.py`,
  `janito/cli/handlers/providers.py`, `janito/cli/handlers/info.py`,
  `janito/web/backend/routers/config.py`,
  `janito/web/backend/routers/config_helpers.py`,
  `tests/test_provider.py`, `tests/test_provider_config.py`,
  `tests/test_show_providers.py`, `tests/test_shell_provider_cmd.py`)
- `ReadFile` and `ReadMultipleFiles` no longer check `.janitoignore`: files
  matched by `.janitoignore` are read like any other file (the matching /
  blocking logic and its tests were removed, and the now-unused
  `is_janitoignored` helper was dropped). The listing, search and find tools
  still always respect `.janitoignore`.
  (`janito/tools/files/read_file.py`,
  `janito/tools/files/read_multiple_files.py`,
  `janito/tools/files/gitignore_utils.py`, `tests/test_janitoignore.py`,
  `docs/tools/files.md`)
- The system exec tools (`RunBashCode`, `RunPythonCode`, `RunPythonFile`,
  `RunPowerShellCode`, `RunGitHubCLI`) no longer cap `stdout`/`stderr` at 50
  lines nor mirror the overflow to a kept temp file.  The full captured output
  is now returned inline in the result dict (still streamed to the screen in
  real-time), and the `stdout_file` / `stderr_file` keys, the
  `Full stdout/stderr available at ...` pointers and the
  `Full stdout stored at <tmp>...` report tails are gone.
  (`janito/tools/system/_streaming.py`, `janito/tools/system/run_bash_code.py`,
  `janito/tools/system/run_python_code.py`,
  `janito/tools/system/run_python_file.py`,
  `janito/tools/system/run_powershell_code.py`,
  `janito/tools/system/run_github_cli.py`,
  `janito/tools/system/_exec_cli.py`, `tests/test_run_bash_code.py`,
  `docs/TOOL.md`)
- `MiniMax-M3` (minimax provider) now has thinking enabled by default. Its
  OpenAI-compatible API takes a structured `thinking` parameter (`type` can be
  `disabled` or `adaptive`; `adaptive` == thinking on), so the built-in default
  is `thinking: {'type': 'adaptive'}` and is sent through as
  `extra_body={'thinking': {'type': 'adaptive'}}` instead of the flag-style
  `enable_thinking`. Thinking values may now be a plain `True` flag or a
  pass-through dict (`apply_thinking_to_extra_body`). (`janito/provider_data.py`,
  `janito/provider_accessors.py`, `janito/provider_models.py`,
  `janito/openai_client/completions_helpers.py`,
  `janito/openai_client/responses_helpers.py`,
  `janito/openai_client/responses_state.py`, `janito/agent/completions.py`,
  `janito/agent/responses.py`, `janito/web/backend/config.py`,
  `janito/web/backend/routers/config.py`, `janito/cli/handlers/*.py`,
  `janito/shell/cmds/status.py`, `docs/configuration/providers.md`,
  `docs/reference/cli-options.md`, `docs/usage/web-ui.md`)
- The built-in `MiniMax-M3` (minimax provider) context window is now 1M input
  tokens (`max_input_tokens: 1000000`), up from 128k.
  (`janito/provider_data.py`)
- The `minimax` provider now uses per-API-type endpoints: the OpenAI-compatible
  base URL `https://api.minimax.io/v1` (Completions/Responses) and the
  Anthropic-compatible base URL `https://api.minimax.io/anthropic` for the
  native Anthropic SDK API type, which is now selectable with
  `--set api-type=Anthropic` / `--api-type Anthropic`.
  (`janito/provider_data.py`, `docs/configuration/providers.md`,
  `tests/test_provider_config.py`)
- The `zai` provider default model is back to `glm-5.2` (the `glm-5.3`
  entry was removed) and its built-in endpoint is back to the standard Z.AI
  platform URL `https://api.z.ai/api/paas/v4/` (the GLM Coding Plan endpoint
  `https://api.z.ai/api/coding/paas/v4` is no longer used).
  (`janito/provider_data.py`, `README.md`,
  `docs/configuration/providers.md`, `tests/test_config_loaders.py`)
- `-S`/`--system-prompt` no longer disables tools; only `-Z`/`--no-system-prompt`
  suppresses them, so a custom system prompt can still use the built-in, Gmail,
  OneDrive and MCP tools. (`janito/cli/session_setup.py`,
  `janito/web/backend/config.py`)
- The `/tools` command (CLI shell and web chat) now shows a warning when tool
  loading is disabled via `--no-tools`, noting that only the skill tools
  (`load_skill`, `read_skill_resource`) remain available.
  (`janito/shell/cmds/tools.py`, `janito/web/backend/routers/tools.py`,
  `janito/web/frontend/js/chatCommands.js`,
  `janito/web/backend/templates/partials/chat_messages.html`,
  `janito/web/backend/templates/partials/tools_dialog.html`,
  `janito/web/frontend/css/tools.css`)

- Modernized type annotations: replaced the deprecated `typing` aliases
  (`List`, `Dict`, `Set`, `Optional`, `Iterator`, `Union`, `Callable`) with
  built-in generics (`list[...]`, `dict[...]`, ...), the `X | Y` union syntax
  and `collections.abc`, and dropped the redundant `"r"` mode from `open()`
  calls. The `pyupgrade` (UP) rule set is now enabled in the ruff lint
  configuration. (`janito/agent/events.py`, `janito/codesearch/*`,
  `janito/shell/*`, `janito/tooling/*`, `janito/tools/*`,
  `janito/config_store.py`, `janito/json_store.py`, `pyproject.toml`)
- Replaced silent exception swallowing with debug-level logging in tool
  discovery (`janito/tools/__init__.py`), the shell toolbar
  (`janito/shell/session.py`) and the web config endpoints
  (`janito/web/backend/routers/config.py`); the unused
  `BaseTool._get_permission_color` helper was removed.
- Internal refactors: `--set-secret`/`--delete-secret` handlers now receive the
  flattened values directly instead of ad-hoc `args` attributes
  (`janito/__main__.py`, `janito/cli/handlers/secrets.py`), and the F2 restart
  keybinding reuses `_reset_conversation` (`janito/shell/interactive.py`).
- `docs/TOOL.md` updated to match the current implementation: schema
  generation now documented as living in `janito/tooling/schema.py` (plus the
  `executor.py` try/except safety net), the `AUTOLOAD_TOOLSETS` list is now
  `["files", "system", "net"]` with `net` and the web-only `janitoweb`
  toolsets added to the architecture tree, the `report_output()` /
  `build_diff()` helpers are documented, and the `Optional[T]`-requiredness
  note, the execute-colour claim (yellow, not red-ish) and the "framework
  does not wrap `run()`" claim were corrected. (`docs/TOOL.md`)

- **codesearch plugin moved out of the repo** — the codesearch plugin (the
  `CodeSearch` tool, the trigram engine and the `/codesearch` shell command)
  now lives in the sibling `../plugins/janito-codesearch-plugin/` directory
  (its Python package is the `codesearch/` subdirectory), loaded with
  `janito --plugin ../plugins/janito-codesearch-plugin/codesearch`.  The
  repo's `plugins/codesearch/` directory is gone; the CLI help, docs and the
  end-to-end plugin test were updated to point at the new location.
  (`janito/cli/parser.py`, `tests/test_plugin_manager.py`, `ARCHITECTURE.md`,
  `docs/PLUGINS.md`, `docs/tools/codesearch.md`,
  `docs/usage/cli-vs-web.md`, `../plugins/janito-codesearch-plugin/*`)

### Added

- New `/read <question>` shell command: sends the prompt to the LLM using the
  main conversation history (unlike `/ask`, which starts a fresh history), but
  with `tools=` filtered to the read-only (`"r"` permission) tools, so the
  model can read/search/fetch but not write or execute.
  (`janito/shell/cmds/read.py`, `janito/shell/cmds/__init__.py`,
  `janito/shell/interactive.py`, `janito/shell/cmds/help.py`,
  `docs/usage/interactive-mode.md`, `docs/usage/cli-vs-web.md`,
  `tests/test_shell_read_cmd.py`)

- New `/write <question>` shell command: the write-only counterpart of
  `/read` — sends the prompt to the LLM using the main conversation history,
  but with `tools=` filtered to the write-only (`"w"` permission) tools, so
  the model can create, modify or delete files/dirs but not read, search or
  execute. Both commands share the permission-based schema filtering in
  `janito/shell/cmds/_tool_filters.py`.
  (`janito/shell/cmds/write.py`, `janito/shell/cmds/_tool_filters.py`,
  `janito/shell/cmds/read.py`, `janito/shell/cmds/__init__.py`,
  `janito/shell/cmds/help.py`, `docs/usage/interactive-mode.md`,
  `docs/usage/cli-vs-web.md`, `tests/test_shell_write_cmd.py`)

- New `--no-tools` flag disables loading of non-skill tools (built-in toolsets,
  Gmail, OneDrive, MCP) while keeping the skill tools (`load_skill`,
  `read_skill_resource`) enabled, so installed skills remain usable without
  any other tool access. (`janito/cli/parser.py`, `janito/__main__.py`,
  `janito/tooling/tools_registry.py`, `janito/openai_client/client_support.py`,
  `janito/web/backend/config.py`, `janito/web/backend/agent/tooling.py`)

- **Plugin system** — plugins are Python-package directories (e.g.
  `plugins/codesearch/`) loaded with the new `--plugin DIR` flag (repeatable).
  A plugin exports `name`, `on_start` (returns `None` or an error string),
  `SYSTEM_PROMPT` (appended to the system prompt), `TOOLS` (tool classes per
  `docs/TOOL.md`) and `CMD_HANDLERS` (`CmdHandler` subclasses registered with
  the shell). Loading a plugin **temporarily** adds its parent directory to
  `sys.path` (enabling relative imports inside the plugin) and restores it
  afterwards. `janito --list-plugins` shows loaded plugins and their
  `on_start` errors. (`janito/plugin_manager.py`, `janito/cli/parser.py`,
  `janito/__main__.py`, `janito/cli/handlers/plugins.py`,
  `janito/tooling/tools_registry.py`, `janito/tools/__init__.py`,
  `janito/system_prompt.py`, `docs/PLUGINS.md`,
  `tests/test_plugin_manager.py`)

- **codesearch migrated to a plugin** — the trigram engine
  (`code_search.py`, `index.py`, `trigram.py`, `candidates.py`), the
  `CodeSearch` tool and a new `/codesearch` shell command
  (`/codesearch update` / `/codesearch recreate`) now live in
  `plugins/codesearch/`. Loading the plugin with
  `janito --plugin plugins/codesearch` creates `.janito/codesearch.db`
  automatically when it is missing (`on_start`). (`plugins/codesearch/`,
  `docs/tools/codesearch.md`)

- **codesearch plugin system prompt** — the plugin now contributes the
  instruction "When searching text on files use the CodeSearch tool before
  the other search tools" to the system prompt, so the model prefers
  `CodeSearch` over the other search tools. (`plugins/codesearch/__init__.py`,
  `tests/test_plugin_manager.py`, `plugins/codesearch/tests/test_plugin.py`)

### Removed

- **`--init-codesearch` flag and built-in codesearch** — the flag and the
  `janito/codesearch/` / `janito/tools/codesearch/` packages are gone; code
  search is now provided by the codesearch plugin (`janito/cli/parser.py`,
  `janito/__main__.py`, `janito/cli/handlers/__init__.py`,
  `janito/tooling/tools_registry.py`). The index is created automatically
  when the plugin loads, or with `/codesearch recreate`.
