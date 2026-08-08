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
- `HeadlessBrowse` in the `net` toolset: renders a URL with headless Google
  Chrome and returns the page's DOM, so JavaScript-generated content is
  captured (unlike the plain-HTTP `GetUrl`). The tool is only loaded when a
  Chrome/Chromium-based browser binary is found (`should_load`), launches
  Chrome with an isolated profile and a virtual-time budget (`wait_ms`) for JS,
  and mirrors `GetUrl`'s truncation and oversized-content-to-temp-file
  behaviour. Falls back from `--headless=new` to the legacy `--headless` flag
  for older Chromium builds. Closes #43.

### Changed

- The code search index no longer stores a per-file SHA-1 content hash.
  `CodeSearch.Update()` now detects changed files by comparing the file's
  last modified time (`mtime`) against the indexed one, avoiding a full read
  of every file on each refresh. Indexes created with the previous schema
  (v1, with a `sha1` column) are automatically rebuilt on the next
  `Create()`/`Update()`.
- `CodeSearch.Find()` (and the `CodeSearch` tool) now performs **whole-word
  matching** and returns **line results** instead of bare file paths.
  Keywords must appear as whole words (`foo` no longer matches `foobar` or
  `foo_bar`) on a single line; the trigram index still narrows the candidate
  files, which are then scanned line by line (files in the index that no
  longer exist on disk are skipped). For `"and"` every keyword must be on
  the same line, for `"or"` any keyword suffices. `Find()` yields
  `CodeSearchMatch(path, lineno, content)` objects, and the tool returns
  `matches` formatted as `path:lineno: content` (the same format as the
  other search tools) plus `total_matches`. This breaks the previous
  filenames-only return contract on purpose; no backwards compatibility is
  kept.
- Enabled ruff's mccabe complexity check (`C901`) in `[tool.ruff.lint]` with
  `max-complexity = 50` in `[tool.ruff.lint.mccabe]`. Closes #44.
