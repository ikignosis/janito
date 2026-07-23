# File Tools

janito provides a complete set of tools for working with the local filesystem:
listing, reading, creating, modifying, searching, and deleting files and directories.

## Availability

File tools are **always available** — the `files` toolset is auto-loaded, so you don't
need any special flag:

```bash
# File tools work in interactive chat
janito

# ...and in single prompts
janito "List all Python files in this project"
```

## Available Tools

| Tool | Description | Permissions |
|------|-------------|-------------|
| `ListFiles` | List files and directories, with pattern filtering | `r` |
| `ReadFile` | Read the full contents of a file | `r` |
| `ReadFileLines` | Read a specific line range from a file | `r` |
| `ReadMultipleFiles` | Read several files in a single call | `r` |
| `SearchText` | Search for exact text across files | `r` |
| `SearchRegex` | Search for regex patterns across files | `r` |
| `CreateFile` | Create a file with the given content | `w` |
| `CreateDirectory` | Create a directory | `w` |
| `ReplaceTextInFile` | Replace text inside a file | `rw` |
| `MoveFile` | Move or rename a file or directory | `rw` |
| `DeleteFile` | Delete a file | `w` |
| `RemoveDirectory` | Remove a directory (optionally recursively) | `w` |

Permission levels: `r` = read, `w` = write, `rw` = read and write. Write-capable tools
are subject to janito's privilege settings.

## Usage

### Example Prompts

```bash
# Explore a directory
janito "List the files in the docs folder"

# Read a file
janito "Show me the contents of README.md"

# Read just part of a large file
janito "Show me lines 100 to 150 of app.py"

# Create a file
janito "Create a file called notes.txt containing 'hello world'"

# Edit a file
janito "In config.py, replace 'debug = False' with 'debug = True'"

# Search for text
janito "Find every file that mentions 'TODO'"

# Search with a regex
janito "Search for all email addresses in the project"

# Clean up
janito "Delete the temp.log file"
```

## Tool Reference

### ListFiles

List files and directories in a path.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | str | `"."` | Directory to list |
| `pattern` | str | `None` | Glob filter, e.g. `"*.py"` |
| `recursive` | bool | `False` | Recurse into subdirectories |
| `max_depth` | int | `None` | Max recursion depth (unlimited if `None`) |
| `respect_gitignore` | bool | `True` | Skip paths matched by `.gitignore` |

### ReadFile

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | str | — | File to read |
| `max_lines` | int | `None` | Cap on lines read (for large files) |

### ReadFileLines

Read a specific line range (1-based indexing).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | str | — | File to read |
| `from_line` | int | `None` | Start line (defaults to beginning) |
| `to_line` | int | `None` | End line (defaults to end of file) |

### ReadMultipleFiles

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepaths` | list | — | List of file paths to read |
| `max_lines` | int | `None` | Max lines per file |

### SearchText

Search for exact text matches.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `paths` | str | — | Space-separated files/directories to search |
| `query` | str | — | Exact text to find |
| `case_sensitive` | bool | `True` | Case-sensitive matching |
| `max_depth` | int | `None` | Max directory depth |
| `max_results` | int | `100` | Max results returned |
| `count_only` | bool | `False` | Return counts instead of lines |
| `respect_gitignore` | bool | `True` | Skip `.gitignore` paths |

### SearchRegex

Search for regular expression patterns. Same parameters as `SearchText`, but uses
`pattern` (a regex) instead of `query`.

### CreateFile

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | str | — | Where to create the file |
| `content` | str | `""` | Content to write |
| `overwrite` | bool | `False` | Overwrite an existing file |

Parent directories are created automatically.

### CreateDirectory

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | str | — | Directory to create |
| `parents` | bool | `False` | Create missing parent directories |
| `exist_ok` | bool | `False` | Don't error if it already exists |

### ReplaceTextInFile

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | str | — | File to modify |
| `old_str` | str | — | Exact text to find |
| `new_str` | str | — | Replacement text |
| `replace_all` | bool | `False` | Replace all occurrences |

If `old_str` is not found, or is found multiple times while `replace_all=False`, the
tool returns an error so you can refine the match.

### MoveFile

Move or rename a file or directory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | str | — | Source path |
| `destination` | str | — | Destination path |
| `overwrite` | bool | `False` | Overwrite an existing destination |
| `create_dirs` | bool | `False` | Create missing parent directories |
| `preserve_metadata` | bool | `True` | Preserve timestamps/permissions |

### DeleteFile

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filepath` | str | — | File to delete |
| `force` | bool | `False` | Allow deleting directories too |

### RemoveDirectory

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | str | — | Directory to remove |
| `recursive` | bool | `False` | Remove contents recursively |
| `force` | bool | `False` | Ignore errors (e.g. missing directory) |

## Tips

1. **Use `respect_gitignore=True`** (the default) when listing or searching to skip
   build artifacts and dependencies.
2. **Use `ReadFileLines`** instead of `ReadFile` for large files to limit output.
3. **Use `count_only=True`** with the search tools to gauge how many matches exist
   before pulling full results.
4. **Provide enough context in `old_str`** for `ReplaceTextInFile` so it matches
   exactly once, or set `replace_all=True` intentionally.

## Direct CLI Testing

Every file tool can be run directly for testing, outside of chat:

```bash
python -m janito.tools.files.list_files . --pattern "*.py" --recursive
python -m janito.tools.files.read_file README.md --max-lines 20
python -m janito.tools.files.search_text . "TODO"
```

Add `--json` for machine-readable output.

## Related Topics

- [Tools Overview](index.md)
- [Gmail Tools](gmail.md)
- [OneDrive Tools](onedrive.md)
- [Skills](skills.md)
- [MCP Support](mcp.md)
