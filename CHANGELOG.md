# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/ikignosis/janito/compare/v4.24.0...HEAD)

Changes since `v4.24.0` (2026-08-13).

### Changed

- **File tools report exclude patterns**: `SearchText`, `SearchRegex`, and
  `FindFiles` now include the `exclude` glob patterns in their `report_start`
  announcement when defined.
- **Simpler ReadFile result message**: `ReadFile` now reports only the number
  of lines read, dropping the explicit line range from the result message.

### Fixed

- **Docs point to the correct repository**: fixed `github.com/joaopinto/janito`
  links in `CHANGELOG.md`, `README_DEV.md` and `RELEASE.md` to reference
  `github.com/ikignosis/janito`.
