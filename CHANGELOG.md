# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.28.0...HEAD)

Changes since `v4.28.0` (2026-08-19).

## [v4.28.0](https://github.com/joaompinto/janito/compare/v4.27.0...v4.28.0) - 2026-08-19

Changes since `v4.27.0` (2026-08-19).

### Added

- **Gemini reasoning configuration**: Added `default_effort_level` (`medium`) and
  updated `supported_reasoning_levels` (`low`, `medium`, `high`) for `gemini-3.7-flash`,
  displaying the default reasoning level in the `--show-providers` and `/status` outputs.

### Fixed

- **Thinking display for Gemini/Google**: `/status`, `--info`, `--show-providers`,
  and `/thinking` now report `N/A (controlled via Reasoning Level)` for Gemini
  models instead of `disabled`, clarifying that thinking is active by default and
  its depth is configured via reasoning levels rather than the boolean thinking toggle.
- **Native Gemini client**: plain-text / non-object tool results are now
  wrapped in a `{"result": ...}` object for `function_response.response`,
  which the `google-genai` SDK requires to be a JSON object. Previously a
  tool returning free-form text (e.g. the library-skills markdown) was sent
  as a raw string and rejected by the SDK's client-side pydantic validation
  with `extra_forbidden` errors on `contents[].Part.role`/`parts` and
  `function_response.response` "Input should be a valid dictionary".
