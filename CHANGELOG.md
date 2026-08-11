# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.22.0...HEAD)

Changes since `v4.22.0` (2026-08-10).

### Added

- **`janito --show-providers`** (`janito/cli/parser.py`,
  `janito/cli/handlers/providers.py`, `janito/__main__.py`): new flag that
  lists every supported provider from `PROVIDER_INFO` — default model, API
  types (the first one is the default), effective endpoint, masked API key,
  thinking/reasoning defaults and token limits — followed by the registered
  provider variants (marked with their base provider); the configured default
  provider is flagged `[active]`. Docs in
  `docs/configuration/providers.md` ("Listing providers") and
  `docs/reference/cli-options.md`. Tests in `tests/test_show_providers.py`.

- **Provider variants** (`janito/general_config.py`, `janito/provider_config.py`,
  `janito/cli/parser.py`, `janito/cli/handlers/variants.py`, web backend +
  frontend): multiple configurations for the same provider, named
  `<provider>-<word>` (e.g. `alibaba-tokenplan`). `--create-variant <name>`
  registers a variant in `config.json` (a `"variants"` entry with `{}`), after
  which the name is accepted anywhere a provider name is used (`-p`/`--provider`,
  `--set provider=`, `--set-api-key`, `--info`, shell `/status`, web combos). A
  variant inherits its base provider's built-in defaults (model, endpoint, API
  types, token limits, reasoning, thinking) while keeping its own per-variant
  config keys (`providers.<name>.*`) and API key (`auth.json`). `--delete-variant
  <name>` removes the entry, the per-variant config and the API key, refusing to
  delete the configured default provider. Unregistered variant-looking names are
  rejected with a `--create-variant` hint. Web: variants appear in the Settings
  drawer's provider list and new "Variants" section (create/delete), plus
  `POST /api/config/variants` and `DELETE /api/config/variants/{name}`. Docs in
  `docs/configuration/variants.md`. Closes #47.

### Fixed

- **`!<command>` shell execution now works with interactive, full-screen
  programs (vim, less, ...)** (`janito/shell/interactive.py`): the command
  previously ran with `capture_output=True`, which gave the child a pipe
  instead of the real terminal and broke TUI programs (“Vim: Warning: Output
  is not to a terminal”). The command now inherits the terminal directly
  (stdin/stdout/stderr) and runs without a timeout, so `!vim` and friends
  work like in a normal shell; the exit code is still reported after the
  command finishes. While the command runs, SIGINT is ignored in the parent
  (mirroring `os.system`) so Ctrl+C is handled by the running program (e.g.
  vim) instead of aborting the wait and orphaning it. On POSIX the terminal
  is forced to cooked mode around the command and restored afterwards, so a
  command that crashes mid-way can't leave the shell with a raw/no-echo
  terminal. Tests in `tests/test_shell_cmd.py`. Closes #48.

### Changed

- **`ReadFile` arguments improved** (`janito/tools/files/read_file.py`): renamed
  `from_line` → `start_line` and replaced the end-line `to_line` parameter with
  `max_lines` (the maximum number of lines to read from `start_line`, clamped at
  EOF), and added `head`/`tail` boolean flags that return only the first/last 10
  lines of the file (they take precedence over the range arguments and cannot be
  combined). The `report_start` announcement now reads `(start at line X, max Y
  lines)` / `(start at line X, until EOF)` (head/tail show `(first 10 lines)` /
  `(last 10 lines)`). Updated the CLI harness, tests, docs, and the web
  tool-card summary to the new arguments. Closes #46.

- **The web chat's tool card for code-execution tools (`RunBashCode`,
  `RunPythonCode`, `RunPowerShellCode`) now shows the submitted `code`
  argument as a code block at the top of the card body, before the tool
  actually executes** — i.e. it is visible as soon as the tool call is made,
  above the live output/result sections (`chatFormat.js::isCodeTool` +
  `templates/partials/chat_messages.html`, styled via `.tool-code` in
  `frontend/css/tools.css`). Added contract tests in
  `tests/web/test_web_bash_code_display.py`.

- **The web chat's message input and Send button are now hidden when there
  is no active session** (e.g. after closing the last conversation): the
  input area (`templates/partials/input_area.html`) is gated on the active
  session id (`x-show="sessionId"`), so it only appears once the user
  selects or creates a conversation in the sidebar. The empty-state banner
  (`templates/partials/chat_banner.html`) now shows "No active
  conversation — select or create one in the sidebar" in that case instead
  of pointing at the (hidden) input box, and closing the active session
  (`clearActive` in `chatStore.js`) clears the stale draft so it doesn't
  resurface when a new conversation is opened. Added contract tests in
  `tests/web/test_web_send_reliability.py`.
