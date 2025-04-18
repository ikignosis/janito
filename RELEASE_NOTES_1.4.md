# Release Notes – Version 1.4

## 1.4.1 (2025-04-19)
- Maintenance release: version bump and documentation updates for 1.4.1.

This document tracks notable changes, enhancements, and fixes for the 1.4 release cycle. Release date: 17/04/2025.

## Added
- `--max-tools` CLI/config parameter to limit the overall maximum number of tool calls within a chat session.

## Changed
- Updated the README documentation.
- `view_file` tool info output now shows `Lines (X-Y)` instead of `StartLine: X | EndLine: Y`.
- "TargetContent not found" in `edit_file` tool is now an info message, not an error.

## Deprecated
- _None_

## Removed
- `--single-tool` CLI/config parameter and all related logic/documentation (parallel tool call disabling).

## Fixed
- _None listed for this release._

## Security
- _None listed for this release._

---

For a complete list of changes, see the project changelog (CHANGELOG.md) or commit history.
