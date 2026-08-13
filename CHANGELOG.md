# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.23.0...HEAD)

Changes since `v4.23.0` (2026-08-12).

### Changed

- **`.janitoignore` file itself is always ignored** (`janito/tools/files/gitignore_utils.py`):
  the `.janitoignore` file is now automatically added to the ignore list, so it
  never appears in `ListFiles`/`FindFiles` listings or `SearchText`/`SearchRegex`
  results (the codesearch indexer skips it too). Other ignore patterns keep
  working as before. Tests updated in `tests/test_janitoignore.py`.
