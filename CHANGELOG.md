# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.12.0...HEAD)

Changes since `v4.12.0` (2026-07-26).

## [v4.12.0](https://github.com/joaopinto/janito/compare/v4.11.0...v4.12.0) - 2026-07-26

Changes since `v4.11.0` (2026-07-25).

### Added

- Add `-c` / `--config-dir` CLI option to override the default `~/.janito` config directory ([a617f82](https://github.com/joaopinto/janito/commit/a617f82)).
- Store `model` and `endpoint` settings per-provider in the config file ([0269b2f](https://github.com/joaopinto/janito/commit/0269b2f)).
- Track `git diff` after prompt processing so file changes made during a session can be reviewed (closes #7) ([4301d5d](https://github.com/joaopinto/janito/commit/4301d5d)).
- Web chat: "Jump to latest" pill with scroll-lock during streaming ([09ff448](https://github.com/joaopinto/janito/commit/09ff448)).
- Show a summary banner with the total of active and skipped tools when the shell starts (#10) ([fa9ae3a](https://github.com/joaopinto/janito/commit/fa9ae3a)).

### Changed

- **Breaking:** migrate provider configuration to a nested, provider-scoped structure and centralize config utilities ([33cd639](https://github.com/joaopinto/janito/commit/33cd639)).
- **Breaking:** replace `OPENAI_*` environment variables with local file-based config resolution ([40b21bd](https://github.com/joaopinto/janito/commit/40b21bd)).
- **Breaking:** remove the `--endpoint` CLI argument in favor of `--set endpoint=...` ([6e1cf3e](https://github.com/joaopinto/janito/commit/6e1cf3e)).
- Make provider resolution explicit and raise a clear error when no provider is configured ([41341bb](https://github.com/joaopinto/janito/commit/41341bb)).
- Make `/multi` single-use and add a web tools summary banner (closes #12) ([933dc55](https://github.com/joaopinto/janito/commit/933dc55)).
- Clarify the interrupt message to mention conversation history rollback ([e5c8b7b](https://github.com/joaopinto/janito/commit/e5c8b7b)).
- Remove git diff execution from the interactive shell (diff is now shown after prompt processing) ([b6eca0e](https://github.com/joaopinto/janito/commit/b6eca0e)).
- Add an AI-generated content disclaimer to the README ([abae470](https://github.com/joaopinto/janito/commit/abae470)).

### Fixed

- Provider-scoped config: fix integer coercion for numeric settings and repair test setup ([ca3ffb3](https://github.com/joaopinto/janito/commit/ca3ffb3)).
- Web chat: show execution time even when it is `0ms`, and improve spacing ([4236898](https://github.com/joaopinto/janito/commit/4236898)).

## [v4.11.0](https://github.com/joaopinto/janito/releases/tag/v4.11.0) - 2026-07-25

See the [release notes](https://github.com/joaopinto/janito/releases/tag/v4.11.0) for earlier changes.
