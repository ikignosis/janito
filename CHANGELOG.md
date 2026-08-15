# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/ikignosis/janito/compare/v4.24.0...HEAD)

Changes since `v4.24.0` (2026-08-13).

### Added

- **`glm-5.3` model for the `zai` provider**: registered as a built-in model
  and made the new default for Z.AI (`PROVIDER_INFO["zai"]["default_model"]`).
  `glm-5.2` remains available.
- **Shell `/provider` command**: switch the provider for the running shell
  session with `/provider <name>` (validated against the supported providers
  and registered variants). The switch is runtime-only: it updates the shell's
  displayed provider/model and rebinds the API client (re-resolving the model
  and API type) without changing the configured default `provider` in
  `config.json` (persist a new default with `--set provider=<name>`). The
  provider name is autocompleted in the shell: after `/provider `, the
  available provider names are suggested as you type. `/provider` with no
  argument lists the current provider and every available one. Switching the
  provider takes effect immediately for the running session and clears the
  LLM conversation history (system prompt preserved) so the new
  provider/model starts fresh — including when the session was started with
  `--provider`.

### Changed

- **`zai` provider endpoint points to the GLM Coding Plan API**: the built-in
  endpoint for the `zai` provider is now
  `https://api.z.ai/api/coding/paas/v4` (the GLM Coding Plan OpenAI Chat
  Completions endpoint). Users on the standard Z.AI platform can override it
  with `--set endpoint=https://api.z.ai/api/paas/v4/`.
- **`/provider` autocomplete offers only usable providers**: the shell
  autocompletion for `/provider <name>` now suggests only providers that
  have an API key stored in `~/.janito/auth.json` (switching to a key-less
  provider would only make the next prompt fail with an authentication
  error). `/provider` with no argument still lists every available
  provider, and `/provider <name>` still accepts any supported provider
  explicitly.
- **File tools report exclude patterns**: `SearchText`, `SearchRegex`, and
  `FindFiles` now include the `exclude` glob patterns in their `report_start`
  announcement when defined.
- **Simpler ReadFile result message**: `ReadFile` now reports only the number
  of lines read, dropping the explicit line range from the result message.
- **Default provider stored in `config.json`, not `auth.json`**: the
  `provider` default (set with `--set provider=<name>` or the web Settings
  drawer) lives only in `~/.janito/config.json`; `auth.json` now holds
  nothing but provider -> API key pairs. Storing an API key no longer
  auto-promotes that provider to the default (the `provider` metadata key
  is no longer written to or read from `auth.json`).
- **Per-model configuration**: per-model settings (max input/output tokens,
  reasoning level, API type, responses-in-server, thinking) moved out of the
  provider level of `PROVIDER_INFO` into a per-provider `models` dict, with a
  `default_model` per provider. `config.json` stores these keys under
  `providers.<provider>.models.<model>.<key>`; the legacy provider-scoped
  locations are no longer read or written ([#50]).

### Fixed

- **Alibaba provider endpoint**: the `alibaba` provider's OpenAI-compatible
  base URL (Chat Completions and Responses API types) pointed at the DashScope
  "apps-protocol" gateway
  (`dashscope-intl.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1`),
  which rejects ordinary DashScope API keys with `Not support` — every prompt
  after `/provider alibaba` (or `--provider alibaba`) returned an empty
  response. The endpoint now uses the plain compatible-mode base URL
  (`dashscope-intl.aliyuncs.com/compatible-mode/v1`).
- **Chat Completions stream surfaces API errors**: when an OpenAI-compatible
  provider (e.g. Alibaba DashScope) rejects a request in-band — a single
  stream chunk with no `choices` carrying `code`/`message` instead of an HTTP
  error — the turn now raises with the provider's message instead of silently
  finishing with an empty response (CLI and web).
- **Docs point to the correct repository**: fixed `github.com/joaopinto/janito`
  links in `CHANGELOG.md`, `README_DEV.md` and `RELEASE.md` to reference
  `github.com/ikignosis/janito`.

[#50]: https://github.com/ikignosis/janito/issues/50
