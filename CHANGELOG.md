# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/ikignosis/janito/compare/v4.25.0...HEAD)

Changes since `v4.25.0` (2026-08-15).

### Changed

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
  `["files", "system", "net", "codesearch"]` with `net`, `codesearch` and the
  web-only `janitoweb` toolsets added to the architecture tree, the
  `report_output()` / `build_diff()` helpers are documented, and the
  `Optional[T]`-requiredness note, the execute-colour claim (yellow, not
  red-ish) and the "framework does not wrap `run()`" claim were corrected.
  (`docs/TOOL.md`)

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
