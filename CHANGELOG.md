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

### Changed

- The CLI token-usage summary now shows the input tokens over the provider's
  default max input tokens, e.g. `In: 54.2k/128k`, mirroring the existing
  `Out: 591/393.2k` format.
- Raise the DeepSeek provider's `default_max_input_tokens` from 128k to 1M.
- Raise the Alibaba (Qwen) provider's `default_max_input_tokens` from 128k to 1M.
