# Release Notes for 1.5.x

## Major Improvements to `replace_text_in_file` Tool

- The info message now displays only the number of lines in the search and replacement text, not a preview of their content. This avoids leaking or cluttering logs with large/multi-line changes.
- Added a guard to prevent accidental replacement of the entire file: if `search_text` is empty, the tool warns and refuses to proceed.
- The file is only written if there are actual changes (i.e., the replacement would modify the file). If nothing changes, the file is left untouched and a clear info message is reported.
- Improved warning handling: empty search text is treated as a warning, not an error, for better user experience.
- If no changes are made, a clear info message is reported and the file is left untouched.

These changes make the tool safer, more predictable, and provide clearer feedback for users.

## New Feature: Vanilla Mode

- Added "vanilla mode" to the agent, allowing operation without any external tools or plugins. This mode is useful for minimal, dependency-free usage and testing scenarios.
