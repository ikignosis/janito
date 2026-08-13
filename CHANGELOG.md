# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.23.0...HEAD)

Changes since `v4.23.0` (2026-08-12).

### Changed

- **Shell and CLI output uses rich tables instead of `====`/`----` headers**:
  - `/prompt` (`janito/shell/cmds/prompt.py`) and `janito --show-system-prompt`
    (`janito/cli/handlers/info.py`) render the default prompt as a rich table
    with per-section rows (Section, Lines, Content); custom (`-S`) prompts are
    shown inside a single-column table.
  - Shell commands `/status`, `/history`, `/tools`, `/mcp`, `/help` and
    `/skills` (`janito/shell/cmds/`) render their output as rich tables.
  - `--info` and `--show-config` (`janito/cli/handlers/info.py`) render the
    resolved/current configuration as a two-column (Key/Value) table.
  - `--show-providers` (`janito/cli/handlers/providers.py`) renders each
    provider as its own two-column table (Model, API types, Endpoint, API key,
    Thinking, Reasoning, Max tokens).
  - `--list-tools` / `--list-mcp` (`janito/cli/handlers/tools.py`) render tools
    grouped per category and MCP services in rich tables.
  - `--list-keys` / `--list-secrets` (`janito/cli/handlers/auth.py` /
    `janito/cli/handlers/secrets.py`) render per-file tables.
  - The interactive `janito --config` wizard (`janito/cli/handlers/config.py`)
    uses panels for its section headers and a table for the summary; the
    OneDrive auth/status output (`janito/cli/handlers/onedrive.py`) renders as
    tables/panels.
  - The now-unused `render_system_prompt_sections` helper was removed from
    `janito/system_prompt.py`; the benchmark script
    (`scripts/provider_token_benchmark.py`) regex for `--list-keys` output was
    updated to the new table rows. Tests updated across
    `tests/test_shell_prompt_cmd.py`, `tests/test_shell_config_cmd.py`,
    `tests/test_shell_skills_cmd.py`, `tests/test_info.py`,
    `tests/test_show_providers.py`, `tests/test_system_prompt.py`,
    `tests/test_provider_token_benchmark.py`.

- **`.janitoignore` file itself is always ignored** (`janito/tools/files/gitignore_utils.py`):
  the `.janitoignore` file is now automatically added to the ignore list, so it
  never appears in `ListFiles`/`FindFiles` listings or `SearchText`/`SearchRegex`
  results (the codesearch indexer skips it too). Other ignore patterns keep
  working as before. Tests updated in `tests/test_janitoignore.py`.

- **Web chat: AskUser questions render inline instead of in a bottom sheet**:
  the in-browser question panel (`prompt_modal.html` and the root-scope modal
  wiring in `app.js`) was removed. When the assistant raises an AskUser
  question, the chat stream now shows a high-attention amber card with the
  question, an answer input and Submit/Skip buttons. Answers are still routed
  back over the raising session's WebSocket; questions raised in background
  sessions surface a toast so they aren't silently waiting in another tab.
