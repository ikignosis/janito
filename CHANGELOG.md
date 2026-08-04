# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.18.1...HEAD)

Changes since `v4.18.1` (2026-08-04).

### Added

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

### Changed

- The CLI token-usage summary now shows the input tokens over the provider's
  default max input tokens, e.g. `In: 54.2k/128k`, mirroring the existing
  `Out: 591/393.2k` format.
- Raise the DeepSeek provider's `default_max_input_tokens` from 128k to 1M.
- Raise the Alibaba (Qwen) provider's `default_max_input_tokens` from 128k to 1M.
