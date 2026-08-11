# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.22.0...HEAD)

Changes since `v4.22.0` (2026-08-10).

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
