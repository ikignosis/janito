## [Unreleased]
- BREAKING: Removed the `overwrite` option from the `create_file` tool. It now only creates new files and fails if the file exists.
- NEW: Added `replace_file` tool, which always overwrites (or creates) the file at the given path.
- Updated documentation and tool registry to reflect these changes.
