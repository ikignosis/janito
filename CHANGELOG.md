# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased](https://github.com/joaopinto/janito/compare/v4.22.0...HEAD)

Changes since `v4.22.0` (2026-08-10).

### Changed

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
