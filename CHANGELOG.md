# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.28.0...HEAD)

Changes since `v4.28.0` (2026-08-19).

### Added

- New `--list-models` CLI flag: lists every model config-available from the
  provider (set via `--provider` or defined in `config.json`) -- the
  provider's built-in models plus any per-model config entries -- flagging
  the default, configured, and current models.

### Fixed

- Clean up system prompt formatting: remove the stray markdown bullet from the
  directory-exploration instruction and the leading blank lines from the
  "Available Skills" section header.
