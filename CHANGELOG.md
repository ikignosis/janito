# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.19.0...HEAD)

Changes since `v4.19.0` (2026-08-06).

### Added

- The file tools (`ListFiles`, `FindFiles`, `SearchText`, `SearchRegex`) now
  respect a `.janitoignore` file in the working directory. It behaves like
  `.gitignore` but is **always** respected: unlike `.gitignore`, it is not
  gated behind the `respect_gitignore` setting (nor the `--no-gitignore` CLI
  flag). Results include `janitoignore_applied` /
  `files_ignored_by_janitoignore` / `janitoignore_ignored` counters and the
  CLI reports "Respecting .janitoignore" and per-file filtered counts.

## [v4.19.0](https://github.com/joaopinto/janito/compare/v4.18.0...v4.19.0) - 2026-08-06

Changes since `v4.18.0` (2026-08-03).

### Added

- The web Settings drawer gains an **Advanced** section (collapsed by
  default) with three per-provider fields: an **Endpoint** text input
  (base-URL override, empty clears it back to the built-in endpoint), an
  **API Type** control (a combobox with one option per supported type,
  bound to the effective value) and a togglable
  **ResponsesInServer** switch that only appears while the API type is
  "Responses".  All three are saved per provider with the drawer's Save
  button via `PATCH /api/config` (stored under
  `providers.<name>.{endpoint,api-type,responses-in-server}` in
  `~/.janito/config.json`) and exposed per provider via
  `GET /api/config/providers` (`api_type`, `supported_api_types`,
  `responses_in_server`, `default_responses_in_server`,
  `responses_in_server_override`).
- Add a per-provider `responses-in-server` config override
  (`--set responses-in-server=true|false` or the web Advanced section):
  `get_responses_in_server_from_provider()` now honours the configured value
  over the built-in default, so a provider's Responses endpoint can be
  switched between server-side (`previous_response_id`) and stateless
  (client re-sends history) conversation handling per deployment.
- Add `anthropic` as a built-in provider (Claude models) with the
  OpenAI-compatible endpoint `https://api.anthropic.com/v1/`, a default model
  of `claude-sonnet-5` (200k input / 64k output tokens, Completions API),
  plus docs, provider-info tests and web provider listing support.
- Print a startup banner (`Janito x.y.z - Working at <cwd>`, with the version
  in cyan and the working directory in magenta) on the shell right before the
  "Running with full privileges" warning.
- The web session-start banner's "N tool(s) active" count is now a link that
  opens a tools info dialog showing the same listing as the `/tools` command
  (built-in tools with permission badges, skipped tools and MCP tools, plus a
  summary footer). The dialog is a compact, bounded modal (capped at 70vh)
  whose tools list scrolls inside it; it reuses the `/tools` data fetcher
  (`_fetchToolsListing`) and lazily loads/caches the listing on first open.
- Add `default_max_input_tokens` (128k) to the built-in per-provider info and
  expose it through `get_default_max_input_tokens_from_provider()` and the web
  providers endpoint.
- Add `default_reasoning_level` (`xhigh`) and `supported_reasoning_levels`
  (`low`/`medium`/`xhigh`) to the Alibaba (Qwen) provider info for its default
  model `qwen3.8-max`.
- Send the reasoning level to the API as `reasoning_effort`: resolved from
  `--reasoning-level`, then the per-provider `reasoning-level` config
  (`--set reasoning-level=...`), then the provider's built-in default. Applies
  to both the CLI (`send_prompt`) and web agent (`build_call_kwargs`) API
  calls, and the web providers endpoint now exposes
  `default_reasoning_level` / `supported_reasoning_levels`.
- Add `default_thinking` to the built-in per-provider info, set to `True` for
  DeepSeek and Alibaba (Qwen) whose models reason by default. Thinking mode
  now resolves from the `--thinking` flag, then the provider's built-in
  default: the CLI (`send_prompt`) and web agent (`build_call_kwargs`) send
  `extra_body={'enable_thinking': True}` automatically for those providers,
  the web config endpoint reports the effective thinking state, and the
  providers endpoint exposes `default_thinking`.
- The web status bar's "thinking" badge is now a runtime toggle button: it
  posts to the new `POST /api/config/thinking` endpoint, which flips thinking
  mode for the running server only (in-memory, never written to
  `~/.janito/config.json`, lost on restart) and applies to the very next
  prompt. The override forces the state in both directions — it can disable
  thinking even for providers that reason by default (DeepSeek, Qwen) — and
  wins over the `--thinking` CLI flag and the provider's built-in
  `default_thinking` (`WebServerConfig.effective_thinking` resolution order:
  runtime override, CLI flag, provider default).
- Add `janito/openai_client/conversations_api.py`, a Responses API
  (`client.responses.create`) counterpart to `completions_api.py` that
  mirrors its behaviour (config resolution, tool loading, MCP support,
  progress spinner, Enter-to-cancel, reasoning panel, used-files report and
  token-usage summary) with one key difference: the conversation history is
  no longer stored/updated on the client side. The Responses API keeps the
  state server-side, so turns are chained with `previous_response_id` (from
  the returned `ConversationResult.response_id`) and tool-call rounds are
  chained internally via `function_call_output` input items; `instructions`
  are only sent on the first turn. Tool schemas are converted up front from
  the shared Chat Completions shape (`name`/`description`/`parameters`
  nested under `function`) to the Responses API shape (top-level `name`)
  via the new `_convert_tools_to_responses_format()` helper, since
  `client.responses.create(tools=...)` rejects the Completions shape with
  `tools[0]: missing field 'name'`. Exposed through the package as
  `send_prompt_responses`, alongside the new `ConversationResult` type.
- Support **stateless** Responses endpoints: a new per-provider
  `responses_in_server` flag in `PROVIDER_INFO` (default `True`, the
  Responses API design) declares whether the provider's `/responses`
  endpoint keeps the conversation server-side and can resolve a
  `previous_response_id`. DeepSeek declares `False` — its endpoint is
  stateless and rejects tool outputs referencing a previous response with
  `No tool call found for tool output with call_id ...`. For such providers
  the Responses client falls back to the Chat Completions model of
  ownership: the full conversation is tracked as Responses input items
  (`ConversationResult.input_items`) and re-sent on every request via the
  new `previous_items` argument, with `function_call` /
  `function_call_output` items and the system instructions (folded in on the
  first turn) forming the history; `previous_response_id` is never sent.
  The interactive shell tracks these items per session (reset on
  F2/`restart`, truncated by `/rollback`) and the wrapper / single-prompt
  paths pass them through, while server-side providers keep the existing
  id-chaining behaviour unchanged.
- Add per-provider `supported_api_types` to `PROVIDER_INFO` — OpenAI declares
  `["Responses", "Completions"]`, every other provider `["Completions"]` —
  and select the API per provider: the **first** entry of the list is the
  built-in default, overridable with `--api-type` or the per-provider
  `--set api-type=...` config (new `resolve_api_type()` in `general_config`).
  `--set api-type=completions|responses` accepts either value in any casing,
  normalizes it to `Completions`/`Responses` when stored, and rejects anything
  else with an error at set time (new `normalize_api_type()` in
  `general_config`). The CLI `chat.py` wrapper now dispatches to
  `conversations_api.send_prompt` (Responses) or `completions_api.send_prompt`
  (Completions) accordingly:
  OpenAI defaults to the Responses API, the interactive shell tracks the
  server-side `previous_response_id` (reset on F2/`restart`,
  `/rollback` resets the server conversation), `/ask` starts a fresh server
  conversation, and `/show_config`, `--info`, `--show-config` and the web
  providers endpoint all surface the resolved API type.
- `janito --info` and the shell `/show_config` command now show the resolved
  `responses_in_server` flag (e.g. `Responses In Server: server-side
  (previous_response_id)` for OpenAI, `stateless (client re-sends history)`
  for DeepSeek) when the effective API type is `Responses`. The line is
  omitted when the API type resolves to `Completions`.
- Add a root-level `RELEASE.md` documenting the four-step release process
  (determine version, run `scripts/promote_changelog.py`, commit the
  changelog, tag), including the bump rules, exact commands and how the
  release workflow validates the changelog.

### Changed

- Remove the "Privileges: read · write · exec" line from the web
  Settings drawer (it duplicated the status-bar badges and exposed internal
  `-r`/`-w`/`-x` flag state); the now-unused `fine-print` utility class was
  dropped with it.
- Rename `janito/openai_client/client.py` to `janito/openai_client/completions_api.py`
  (the module now lives alongside the rest of the web backend call stack);
  imports and docstring references are updated accordingly.
- Rename the built-in per-provider info fields in `PROVIDER_INFO` to drop the
  redundant `default_` prefix (every value in the entry is a default):
  `default_model` -> `model`, `default_max_input_tokens` -> `max_input_tokens`,
  `default_max_output_tokens` -> `max_output_tokens`,
  `default_reasoning_level` -> `reasoning_level` and `default_thinking` ->
  `thinking`. The accessor functions (`get_default_*_from_provider()`) and the
  web providers endpoint response keep their existing names.
- The startup banner now maps the home directory to `~` when showing the
  working directory, e.g. `Janito 0.2.0 - Working at ~/janito` instead of the
  full path.
- The CLI token-usage summary now shows the input tokens over the provider's
  default max input tokens, e.g. `In: 54.2k/128k`, mirroring the existing
  `Out: 591/393.2k` format.
- Raise the DeepSeek provider's `default_max_input_tokens` from 128k to 1M.
- Raise the Alibaba (Qwen) provider's `default_max_input_tokens` from 128k to 1M.
- Update the built-in provider defaults in `PROVIDER_INFO`: the OpenAI
  provider's default model is now `gpt-5.6-luna` (with `max_input_tokens`
  raised from 128k to 1050000), the Alibaba (Qwen) endpoint now points at the
  DashScope apps-protocol compatible-mode URL
  (`https://dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1`),
  and the DeepSeek provider's `max_input_tokens` is now `1048576` (an exact
  1M = 2^20) instead of `1000000`.
- Rename the interactive shell command `/config` to `/show_config`; it now also
  displays the resolved reasoning level.
- The web topbar's dark/light theme toggle now sits at the rightmost position,
  after the provider switcher, MCP and Settings buttons.
- The web status bar now lists the provider before the model, matching the
  Settings drawer and provider switcher ordering (provider hosts the model).
- The web status bar now shows the selected (effective) provider's default
  model with a muted `(default)` marker instead of `(not set)` when no model
  is explicitly configured or CLI-pinned — resolving the same way as the
  provider switcher and Settings drawer (configured override first, then the
  provider's built-in default). `(not set)` remains only when even the
  provider has no default model.
- The `ReplaceTextInFile` tool now prints a syntax-highlighted unified diff
  of the change (`BaseTool.report_diff`, which delegates to the new
  `report_diff` reporter) before its success message, so every replacement
  shows exactly what changed.
- Move the CLI tool-execution loop out of `janito/openai_client/client.py`
  into a new `ToolExecutor` class in `janito/tooling/executor.py`. The
  executor owns routing each tool call to the MCP manager or the built-in
  tools registry, usage / used-files / changes tracking, and producing the
  `tool`-role messages appended to the conversation history (including the
  structured error result for failed calls); `send_prompt` now delegates to
  it via a single `handle_tool_calls(...)` call. Behaviour is unchanged.

### Fixed

- The shell's `/cmd` autocompletion no longer triggers on a `/` that appears
  in the middle of the line (e.g. `hello /t`): suggestions are now only
  offered when the `/` token is the first one on the line (leading
  whitespace is still allowed).
- The Responses API client (`conversations_api.send_prompt`) no longer sends
  the now-invalid `include=["usage"]` parameter: `usage` is no longer a
  supported value for `include` in the Responses API (the parameter now only
  accepts tool-related values such as `file_search_call.results`). Token
  usage is delivered by default on the final `response.completed` event (it
  is part of the Response object), which the stream consumer already reads
  via `event.response.usage`.
- The Responses API client (`conversations_api.send_prompt`) no longer
  **silently returns an empty response** when a provider streams an API error
  as an SSE event the OpenAI SDK cannot type (`event.type is None` but the
  payload carries `code`/`message` attributes) — e.g. Alibaba DashScope's
  `/responses` endpoint rejecting an unsupported model with
  `code='InvalidParameter'`, `message="Unsupported model: 'qwen3.8-max'."`.
  Such events now raise a clear `RuntimeError` with the server's message.
  The client also raises instead of returning empty on a zero-event stream
  and on a server-side response that reports no response id and produces
  neither content nor tool calls (the raised error names the model). An
  Enter-to-cancel short-circuit is still treated as a cancellation, not as
  an empty stream.
- The Alibaba (Qwen) provider now defaults to the **Completions** API
  (`supported_api_types` is `["Completions", "Responses"]` instead of
  `["Responses", "Completions"]`): DashScope's `/responses` endpoint does not
  (yet) support the provider's default model `qwen3.8-max`, so the
  out-of-the-box provider must use the API where the model works. The
  Responses API remains selectable per-provider with `--set api-type=Responses`
  or per-call with `--api-type responses` (using a model the endpoint
  supports, e.g. `qwen3.7-max`).
