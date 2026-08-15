# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/ikignosis/janito/compare/v4.25.0...HEAD)

Changes since `v4.25.0` (2026-08-15).

### Changed

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
