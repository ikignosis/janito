# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.28.0...HEAD)

Changes since `v4.28.0` (2026-08-19).

### Added

- New `/api_types` shell command: lists the API types supported by each
  built-in provider/model (e.g. `Responses` / `Completions`, plus native-SDK
  types such as `Anthropic` / `DashScope` / `Gemini`), marking each model's
  built-in default API type.
- New `--list-models` CLI flag: lists every model config-available from the
  provider (set via `--provider` or defined in `config.json`) -- the
  provider's built-in models plus any per-model config entries -- flagging
  the default, configured, and current models.
- New `openrouter` provider: accesses models from many providers behind
  OpenRouter's single OpenAI-compatible endpoint
  (`https://openrouter.ai/api/v1`, Chat Completions API).  Like `custom` it
  has no built-in default model -- its `default_model` is the `"custom"`
  placeholder whose `models.custom` entry only carries built-in defaults
  (the default API type) -- so the user must supply the model explicitly
  (`--model` or `providers.openrouter.model` in `config.json`); when it
  cannot be resolved, runtime configuration fails with an actionable message
  instead of silently sending the placeholder to the API.  The
  `--show-config`, `--list-models` and `--show-providers` displays no longer
  present the placeholder as a usable default/current model.

### Changed

- The `restart` shell command is renamed to `clear` (Clear conversation and
  start a new one); the old `restart` name is no longer available.
- The `/rollback` shell command is renamed to `/rewind` (Rewind conversation
  to a previous message); the old `/rollback` name is no longer available.
- The `alibaba` provider's built-in default model (`qwen3.8-max`) now
  defaults to the Responses API instead of Chat Completions. The Completions
  API remains fully supported and can be selected with
  `--set api-type=Completions` / `--api-type completions`.

### Fixed

- Clean up system prompt formatting: remove the stray markdown bullet from the
  directory-exploration instruction and the leading blank lines from the
  "Available Skills" section header.
