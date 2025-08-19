# Code Analyzer Plugin

## Overview

The Code Analyzer plugin provides tools for understanding and searching code structure. This plugin enables developers to analyze codebases, navigate file structures, and perform advanced text searches across projects.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|
| `get_file_outline` | Extract file structure | Analyzes a file to identify classes, functions, methods, and other structural elements |
| `search_outline` | Search within file outlines | Searches for specific structural elements (classes, functions) within file outlines |
| `search_text` | Full-text search across files | Performs text searches across multiple files with support for regex and case sensitivity |

## Usage Examples

### Getting File Structure
```json
{
  "tool": "get_file_outline",
  "path": "src/main.py"
}
```

### Searching for Functions
```json
{
  "tool": "search_outline",
  "path": "src/",
  "query": "function:calculate"
}
```

### Finding Code Patterns
```json
{
  "tool": "search_text",
  "paths": ".",
  "query": "import requests",
  "use_regex": false
}
```

## Configuration

This plugin does not require any specific configuration and uses default search parameters.

## Security Considerations

- File access is limited to the project directory and subdirectories
- Respects .gitignore rules to avoid searching in ignored files/directories
- Large file analysis is rate-limited to prevent performance issues

## Integration

The Code Analyzer plugin integrates with the code intelligence system to provide:

- Code navigation capabilities
- Structural understanding for AI-assisted coding
- Pattern recognition for code refactoring suggestions
- Dependency analysis through import searching

This enables more sophisticated code understanding and manipulation capabilities within the Janito ecosystem.