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
  `max-complexity = 10` in `[tool.ruff.lint.mccabe]`. Closes #44.
- Reduced the cyclomatic complexity of the remaining hot functions so the
  whole codebase passes `ruff check` with `max-complexity = 10` (was 46 `C901`
  violations). All refactors are behaviour-preserving:
  - The CLI entry point (`janito/__main__.py`) was split into a dispatch
    table plus small setup/batch-config helpers; the `--config` wizard
    (`janito/cli/handlers/config.py`), `--info` resolution and the
    interactive shell loop were decomposed into focused helpers.
  - The `SearchText` and `SearchRegex` tools now share their directory
    walking / ignore / exclude / aggregation logic via a new common base
    module `janito/tools/files/search_base.py`; each tool keeps only its
    per-line matcher, `run()` and CLI harness (each file roughly halved).
  - The file tools (`ListFiles`, `MoveFile`, `RemoveDirectory`,
    `ReadMultipleFiles`) extract their walk/validate/move logic into small
    private helpers.
  - The Gmail tools reuse shared credential fetching, IMAP connection and
    search-criteria helpers in `janito/tools/gmail/imap_utils.py`; the
    OneDrive tools (`base_client`, `list_files`, `read_file`,
    `download_file`, `__main__`) extract request/format helpers.
  - `CreateImage`, `WebSearch`, `CodeSearch.Find`, the web agent's
    `stream_prompt`/`StreamAccumulator`, the WebSocket loop and
    `patch_config` were decomposed into small helpers, and
    `scripts/promote_changelog.py` splits out version/date/section
    resolution.
- Split the remaining production Python files over 600 lines into focused
  modules. Every refactor is behaviour-preserving (no public API changed;
  moved helpers are re-exported from their original modules so existing
  imports and test monkeypatches keep working):
  - The four API clients (`janito/openai_client/completions_api.py`,
    `conversations_api.py`, `anthropic_api.py` and `janito/dashscope_api.py`)
    now share their duplicated support code (token formatting, MCP loading,
    Rich console output, auth-error explainer) from
    `janito/openai_client/client_support.py`, and each client's stream
    consumption moved to its own module (`completions_stream.py`,
    `responses_stream.py`, `anthropic_stream.py`, `dashscope_stream.py`);
    the Responses conversation-state setup moved to
    `responses_state.py`. Each client file shrank below 600 lines.
  - `janito/general_config.py` now only holds the core config storage and
    key-resolution primitives; the per-provider loaders moved to
    `janito/config_loaders.py` and the `--set`/`--get`/`--unset` CLI helpers
    plus `ProviderRequiredError` moved to `janito/config_cli.py`.
  - `janito/provider_config.py` keeps the accessor functions while the
    static provider registry moved to `janito/provider_data.py`.
  - `janito/tools/files/find_files.py` delegates its pure filter helpers to
    `janito/tools/files/find_files_utils.py` and its standalone CLI harness
    to `janito/tools/files/find_files_cli.py`.
  - `janito/codesearch/code_search.py` delegates candidate selection and
    line scanning (plus `MATCH`/`CodeSearchMatch`) to
    `janito/codesearch/candidates.py`.
  - The web config router (`janito/web/backend/routers/config.py`) moved its
    per-provider `PATCH /api/config` helpers to
    `janito/web/backend/routers/config_helpers.py`.
