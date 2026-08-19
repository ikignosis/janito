# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaompinto/janito/compare/v4.27.0...HEAD)

Changes since `v4.27.0` (2026-08-19).

### Fixed

- **Native Gemini client**: plain-text / non-object tool results are now
  wrapped in a `{"result": ...}` object for `function_response.response`,
  which the `google-genai` SDK requires to be a JSON object. Previously a
  tool returning free-form text (e.g. the library-skills markdown) was sent
  as a raw string and rejected by the SDK's client-side pydantic validation
  with `extra_forbidden` errors on `contents[].Part.role`/`parts` and
  `function_response.response` "Input should be a valid dictionary".
