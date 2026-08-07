# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.20.0...HEAD)

Changes since `v4.20.0` (2026-08-07).

### Added

- `exclude` parameter on `SearchText` and `SearchRegex` to skip files and
  directories via space-separated glob patterns (e.g.
  `"*/node_modules/* */__pycache__/*"`). `FindFiles` now also prunes excluded
  directories during the walk instead of only filtering entries, so the three
  search tools behave consistently. Excluded directories are not walked into,
  single-file roots are matched against their basename, and the parameter works
  in `count_only` mode too. The shared glob matcher was extracted into
  `janito/tools/files/glob_utils.py`.

### Changed

- The code search index no longer stores a per-file SHA-1 content hash.
  `CodeSearch.Update()` now detects changed files by comparing the file's
  last modified time (`mtime`) against the indexed one, avoiding a full read
  of every file on each refresh. Indexes created with the previous schema
  (v1, with a `sha1` column) are automatically rebuilt on the next
  `Create()`/`Update()`.
