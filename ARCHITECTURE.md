# Architecture

This document summarizes the architecture of **janito**, a development agent
with function calling, MCP support and skills. It runs through two interfaces
built on the same engine: a terminal CLI/shell and an (alpha) browser-based
web UI.

---

## Overview

Janito is a Python 3.10+ application organized as a single `janito` package
plus a `tests/` suite. At a high level it is a loop:

```
user prompt ──► resolve config ──► create SDK client ──► stream model response
                                                              │
                                              model wants tools? │
                                                              ▼
                                                     execute tools
                                                              │
                                                              ▼
                                                   append results, loop
                                                              │
                                              no more tools?   │
                                                              ▼
                                                      display final answer
```

Everything else — CLI parsing, tool discovery, MCP, skills, the web UI,
configuration — exists to feed or present this loop.

### Top-level layout

| Path | Responsibility |
|------|----------------|
| `janito/__main__.py` | Entry point: argument parsing, dispatch, runtime setup |
| `janito/cli/` | CLI parsing, chat modes, flag-driven command handlers |
| `janito/shell/` | Interactive prompt_toolkit shell and `/`-commands |
| `janito/agent/` | Shared per-API adapters used by both the CLI and web loops |
| `janito/openai_client/` | API clients and the shared agent-loop pipeline |
| `janito/tooling/` | Tool framework: registry, executor, skills, tracking |
| `janito/tools/` | Built-in tool implementations, organized in toolsets |
| `janito/mcp_client/` + `mcp_manager.py` | MCP server connections and tool routing |
| `janito/web/` | FastAPI web backend + plain HTML/JS/CSS frontend |
| `janito/plugin_manager.py` | Plugin loader: contract validation, scoped `sys.path`, registration |
| `../plugins/` (outside the repo) | Optional plugins (e.g. `janito-codesearch-plugin/`) loaded with `--plugin DIR` |
| `janito/*config*.py`, `provider_*.py` | Configuration storage, loaders, provider registry |
| `docs/`, `mkdocs.yml` | MkDocs documentation site |

---

## Entry point & CLI dispatch

`janito/__main__.py` (`main()`) is the single entry point (also registered as
the `janito` console script). Flow:

1. **Parse args** with `janito/cli/parser.py` (argparse).
2. **Setup runtime** (`_setup_runtime`): apply `-c/--config-dir`, `--local`,
   logging, normalize `--provider`, and apply `-r/-w/-x` privilege flags into
   the module-level `running_privileges` (used later by tool discovery).
3. **Batch config ops** (`--set/--unset/--get/--set-secret/--delete-secret`)
   via `_handle_batch_config`.
4. **Load plugins** via `janito/plugin_manager.py`: plugins autoloaded from
   `~/.janito/plugins` (`load_installed_plugins`, unless `--no-plugins`) plus
   those requested with `--plugin DIR` (`load_plugins`, repeatable). For each
   plugin, its parent dir is temporarily added to `sys.path`, the package is
   imported, the contract is validated, `on_start` is called, and its tools,
   `/`-commands and system-prompt sections are registered — all before any
   registry/shell access. Plugin tools are **not** gated by `--no-tools`;
   use `--no-plugins` to disable autoloading.
5. **Flag-driven commands** (`--info`, `--config`, `--list-*`,
   `--set-api-key`, `--install-skill`, ...) via
   `_dispatch_flag_command` → handlers in `janito/cli/handlers/`.
6. **Validate runtime config** (`validate_runtime_config`) — API key, endpoint
   and model must resolve before any session starts.
7. **Dispatch to a mode**:
   - `--web` → `janito/web/backend/app.py:run_web` (checks the optional
     `[web]` extras first);
   - stdin pipe → single-prompt mode;
   - `--prompt` → `run_single_prompt`; otherwise `run_interactive_chat`
     (both in `janito/cli/chat.py`).

`janito/cli/chat.py` builds a `send_prompt_func` bound to the resolved API
type (Responses / Completions / Anthropic / DashScope) and drives either the
interactive shell or a single prompt. `janito/cli/session_setup.py` decides
the effective system prompt and which toolsets to enable.

---

## Interfaces

### Terminal CLI / shell

- **Single prompt**: one turn, exit. `echo ... | janito` and `janito "..."`.
- **Interactive chat** (`janito/shell/interactive.py`): prompt_toolkit-based
  shell with file-backed history, a bottom toolbar (model/provider), key
  bindings (restart, "do it", cancel), a command completer, and `/`-commands
  (`janito/shell/cmds/`): `/rollback`, `/history`, `/priv`, `/mcp`, `/skills`,
  `/tools`, `/changes`, `/ask`, `/multi`, ... Commands are registered through
  a small registry (`cmds/registry.py`).

### Web UI (alpha)

`janito --web` runs a FastAPI server (see [Web backend](#web-backend)) with a
browser chat interface served as static HTML/JS/CSS (no build step).

---

## Agent loop & API clients

The heart of the engine is a **template-method turn pipeline** defined in
`janito/openai_client/base_client.py` (`Client.send`), shared by four clients:

| Client | API type | File |
|--------|----------|------|
| Completions | `chat.completions` | `openai_client/completions_api.py` |
| Responses | `/responses` | `openai_client/conversations_api.py` |
| Anthropic | native `anthropic` SDK | `openai_client/anthropic_api.py` |
| DashScope | native `dashscope` SDK | `dashscope_api.py` + `openai_client/dashscope_stream.py` |

The pipeline per turn:

1. Reset per-prompt tracking (`clear_changes`, `reset_used_files`).
2. Resolve `(base_url, api_key, model)` from CLI args / config / provider data.
3. Create the SDK client; load MCP services and tools (if enabled).
4. Create a `ToolExecutor` (tool-call routing + bookkeeping).
5. Resolve tool schemas (built-in registry + MCP), model settings
   (max tokens, thinking, reasoning level).
6. Loop: stream a response → display reasoning/content → if tool calls were
   requested, execute them (see [Tool execution](#tool-execution)) and loop
   again; otherwise finalize (usage summary, reports, return value).

The web loop (`janito/web/backend/agent/loop.py`) drives the **same turn
pipeline asynchronously**, yielding structured events instead of printing
Rich output. Both loops share the per-API adapter layer in `janito/agent/`
(`completions.py`, `responses.py`, `anthropic.py`, `dashscope.py`, `usage.py`,
`events.py`), so API-specific call-kwargs building, stream accumulation and
history conversion are implemented once.

---

## Tooling system

### Discovery & registry (`janito/tooling/`)

- **`tools_registry.py`** — lazy, module-level `ToolsRegistry` singleton:
  - `ensure_initialized()` runs discovery on first access so privilege flags
    are set before tools are filtered;
  - autoloads the `files`, `system`, `net` toolsets;
  - `get_function_schema()` generates OpenAI-compatible JSON schemas from a
    tool's type hints and docstring;
  - `add_toolset()` enables on-demand toolsets (janitoweb);
  - `register_plugin_tools()` registers tool classes contributed by plugins
    (gated by `--no-tools` like any other non-skill tool);
  - `enable_skills()/disable_skills()` toggle skill tools.

- **`executor.py`** — `ToolExecutor` + shared `run_tool()` core (the
  single tool-execution path used by both the CLI and web loops):
  - routes each call to the MCP manager (tools prefixed with a `service_`
    name) or the built-in registry;
  - tracks tool usage, used files and changes (best-effort);
  - never raises: failures become `{"success": False, "error": ...}` results
    so the model can react.

- **`base_tool.py` / `decorator.py`** — `BaseTool` ABC and the
  `@tool(permissions="...")` decorator marking a class as a tool.

- **`reporter.py` / `prompting.py`** — pluggable progress-report and
  user-prompt handlers (Rich console in the CLI, WebSocket frames in web
  mode).

- **`skills_provider.py`** — progressive-disclosure skills: advertise
  (~100 tokens) in the system prompt, load full `SKILL.md` when activated,
  read resources on demand. Skills are discovered from `~/.janito/skills`
  and `.janito/skills` (local wins).

- **`changes.py`, `used_files.py`, `tools_usage.py`** — per-prompt tracking
  feeding `/changes`, "Used files" reports and tool stats.

### Toolsets (`janito/tools/`)

Tools are grouped in directories (`files/`, `system/`, `net/`,
`janitoweb/`). `discover_toolsets()` in
`janito/tools/__init__.py` scans each toolset for `@tool`-marked classes,
runs their `should_load()` gate (missing binaries, credentials, platform),
checks `_tool_permissions` against `running_privileges`, and wraps each class
as a callable with the `run()` signature. `wrap_tool_class()` /
`discover_module_tools()` expose the same pipeline for arbitrary modules so
the plugin manager can register tools from `plugins/*/tools/`.

### Plugins (`janito/plugin_manager.py`)

`load_plugin()` temporarily adds the plugin's **parent directory** to
`sys.path`, imports the package (enabling relative imports inside the
plugin), validates the contract (`name`, `on_start`, `SYSTEM_PROMPT`,
`TOOLS`, `CMD_HANDLERS`), calls `on_start`, and registers the contributed
tools (`ToolsRegistry.register_plugin_tools`), commands
(`shell/cmds/registry.register_command`) and system-prompt sections
(`system_prompt.register_plugin_system_prompt`). `load_installed_plugins()`
autoloads every package directory under `~/.janito/plugins` (installed with
`janito --install-plugin <github_url>`); `--no-plugins` skips this autoload
but still loads `--plugin DIR` requests. Plugin tool registration is
**not** gated by `--no-tools` (the `--no-tools` flag only disables built-in
tools). See `docs/PLUGINS.md`.

### Privileges

`janito/privileges.py` defines a `Privileges` dataclass (READ/WRITE/EXEC) and
a module-level `running_privileges`. When `-r/-w/-x` are passed, tools whose
declared permissions are not satisfied are skipped during discovery with a
recorded reason (`get_skipped_tools()`).

---

## MCP support

- **`janito/mcp_manager.py`** — `MCPManager` manages multiple connected
  services: `load_services()`, transport lifecycle, tool listing/caching,
  and `call_tool()` routing by service prefix.
- **`janito/mcp_client/`** — transport layer: `stdio.py` (subprocess) and
  `http.py` (streamable HTTP), with a `factory.py` selecting the transport
  from `mcp_config.py` service definitions.
- Services are configured interactively via the `/mcp` shell command or
  `--list-mcp`, stored in the config store, and loaded at the start of every
  turn when MCP is enabled.

---

## Web backend

`janito/web/backend/` (FastAPI + uvicorn, optional `[web]` extras):

- **`app.py`** — app factory: mounts API routers (`/api/chat`, `/api/config`,
  `/api/tools`, `/api/mcp`, `/api/images`, `/api/health`), session manager,
  token-auth middleware and CORS, and serves the frontend via Jinja2
  templates + static files.
- **`session.py` / `session_store.py`** — TTL-based `SessionManager` with
  conversations persisted to `.janito/sessions/` so they survive restarts.
- **`security.py`** — optional bearer-token auth (`JANITO_WEB_TOKEN`) and CORS.
- **`agent/`** — the async agent loop (`loop.py` orchestrates; `turn.py`
  runs tool turns; `call.py` is the Completions runner; `responses.py`,
  `anthropic.py`, `dashscope.py` are the other API runners). Tool calls run
  through the shared `run_tool` core in a worker thread
  (`asyncio.to_thread`).
- **`events.py` / `prompts.py`** — structured SSE/WebSocket events and the
  web AskUser prompt handler.
- **Frontend** (`janito/web/frontend/`): plain HTML/JS/CSS (Alpine.js) with
  WebSocket chat, session list, settings drawer, tool-call cards and a prompt
  modal.

---

## Code search

`../plugins/janito-codesearch-plugin/` powers the `CodeSearch`
tool with a **SQLite-based
inverted trigram index**:

- `index.py` — schema (files, trigrams posting lists) and the `Index` class;
- `trigram.py` — trigram extraction;
- `candidates.py` — candidate file scoring/ranking;
- `code_search.py` — the query layer (and the tool wraps it).

The plugin's `on_start()` creates the index at `.janito/codesearch.db`
when it is missing; the `/codesearch` shell command maintains it
(`/codesearch update` / `/codesearch recreate`). Load with
`janito --plugin ../plugins/janito-codesearch-plugin`.

---

## Configuration

Configuration lives in the config dir (default `~/.janito/`, overridable with
`-c/--config-dir` or local `.janito/` with `--local`):

| Store | File | Contents |
|-------|------|----------|
| Config | `config.json` | provider, model, tokens, api-type, endpoint, MCP services, ... |
| Auth | `auth.json` | API keys per provider |
| Secrets | `secrets.json` | additional named secrets |

Key modules:

- **`config_dir.py`** — config-dir resolution and local-mode flag.
- **`json_store.py`** — thread-safe read/write primitives for the JSON stores.
- **`general_config.py`** — config-resolution helpers (`load_provider_from_config`,
  `determine_provider`, `get_active_provider`, `resolve_api_type()`).
  Config keys are scoped: flat keys (e.g. `provider`), **provider-scoped** keys
  (`model`, `endpoint` under `providers.<name>.<key>`) and **model-scoped**
  keys (`max-input-tokens`, `max-output-tokens`, `reasoning-level`, `api-type`,
  `responses-in-server` under `providers.<name>.models.<model>.<key>`).  The
  storage and per-key logic live in the focused modules below.
- **`config_keys.py`** — key constants (`PROVIDER_SCOPED_KEYS`,
  `MODEL_SCOPED_KEYS`) and the helpers that build/parse dotted keys
  (`model_config_key`, `model_scoped_config_key`, `normalize_api_type`,
  `get_masked_api_key`, ...).
- **`config_store.py`** — `ConfigStore` read/write primitives plus the
  `load_config` / `get_config_value` / `set_config_value` ... delegators.
- **`config_loaders.py`** — per-provider loaders (`load_model_from_config`,
  `load_max_output_tokens`, ...).
- **`config_cli.py`** — CLI helpers for the `--set/--get/--unset` family
  (provider-scoped and model-scoped key resolution).
- **`config_variants.py`** — provider variant management (`load_variants`,
  `create_variant`, `delete_variant`, ...).
- **`providers/`** — per-provider configuration package. The static
  provider registry is split into one `config.py` module per provider
  (`janito/providers/<name>/config.py`, each exporting that provider's
  `PROVIDER_CONFIG` entry); the package `__init__.py` assembles them into
  the internal `_PROVIDER_CONFIGS` dict, keeps the `REQUIRES_BY_API_TYPE`
  optional-package map and the `CUSTOM_ENDPOINT` marker, and exposes
  `get_provider_config(provider, model=None)` for direct (model-scoped)
  lookups. Each provider entry carries provider-level fields
  (`default_model`, `endpoint`, `endpoint_by_api_type`) plus a per-provider
  **`models`** dict with the model-level fields (`supported_api_types`,
  `default_api_type`, token limits, reasoning levels, `thinking`,
  `responses_in_server`). The `custom`
  provider ships no models (`default_model: None`, `models: {}`).
  `janito/providers/template/config.py` is the documentation template for
  these entries: it is not a real provider (never registered in
  `_PROVIDER_CONFIGS`) and comments every possible CONFIG option, so new
  providers are written by copying it and filling in the values.
- **`provider_models.py`** — the typed accessors: `Provider` (with
  `model_config(model)` and per-model accessors defaulting to the provider's
  default model) and `ModelConfig` (typed accessors over one model entry).
- **`provider_registry.py`** — `ProviderRegistry` (case-insensitive lookup
  over `janito.providers._PROVIDER_CONFIGS`, including registered variants)
  and the `parse_variant_name` / `is_variant_style_name` helpers.
- **`provider_accessors.py`** — the module-level `get_*_from_provider`
  helpers (defaults, endpoints, API-type validation, ...) that accept an
  optional `model` argument.
- **`provider_validation.py`** — provider name validation / listing helpers
  (`validate_provider_name`, `is_supported_provider`, `list_variants`, ...).
- **`auth_config.py`, `secrets_config.py`, `mcp_config.py`** — auth, secrets
  and MCP service stores.

The system prompt (`janito/system_prompt.py`) composes the base prompt, the
skills advertisement section, the current project's `AGENTS.md` content, and
any loaded plugins' `SYSTEM_PROMPT` sections. The composition is built from
ordered sections (`base`, `skills`, `agents.md`, `plugins:<name>`) whose text
and line counts are tracked (`get_system_prompt_sections`); the shell
`/prompt` command and `janito --show-system-prompt` display each section as a
row of a rich table (Section, Lines, Content).

---

## A typical turn (end to end)

1. User runs `janito "fix the test"` (or chats in the shell / web UI).
2. `__main__` resolves config, validates runtime, dispatches to
   `run_single_prompt` / `run_interactive_chat`.
3. The chosen API client (`Client.send` pipeline) streams the model response.
4. If the model emits tool calls, `ToolExecutor` → `run_tool()` executes them
   (built-in registry or MCP), tracking usage/used-files/changes, and the
   results are appended to the conversation.
5. The loop repeats until the model answers; the final answer is displayed
   (Rich in the CLI, events/WebSocket in web mode) with a token-usage summary.

---

## Testing & quality

- `tests/` — pytest suite covering clients, tooling, config, shell commands,
  skills, the plugin framework and web (`tests/web/`); the codesearch plugin
  carries its own tests under
  `../plugins/janito-codesearch-plugin/tests/`.
- `tox.ini` + `pyproject.toml` — tox environments, ruff linting/isort.
- `.pre-commit-config.yaml` + `.secrets.baseline` — pre-commit hooks and
  detect-secrets baseline.
