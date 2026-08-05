# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.18.1...HEAD)

Changes since `v4.18.1` (2026-08-04).

### Added

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

### Changed

- The startup banner now maps the home directory to `~` when showing the
  working directory, e.g. `Janito 0.2.0 - Working at ~/janito` instead of the
  full path.
- The CLI token-usage summary now shows the input tokens over the provider's
  default max input tokens, e.g. `In: 54.2k/128k`, mirroring the existing
  `Out: 591/393.2k` format.
- Raise the DeepSeek provider's `default_max_input_tokens` from 128k to 1M.
- Raise the Alibaba (Qwen) provider's `default_max_input_tokens` from 128k to 1M.
- Rename the interactive shell command `/config` to `/show_config`; it now also
  displays the resolved reasoning level.
