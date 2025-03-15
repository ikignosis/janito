# Text Editor Tool Implementation Guide

This document outlines the implementation requirements for the `str_replace_editor` tool in Janito, based on the [Anthropic Claude Text Editor Tool specification](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/text-editor-tool).

## Current Implementation Status

- ✅ Basic tool structure created in `janito/tools/str_replace_editor.py`
- ✅ Tool registered in Agent initialization with `text_editor_tool` parameter
- ✅ All commands implemented and tested
- ✅ Path normalization for `/repo/` paths and other absolute paths

## Commands Implemented

The text editor tool supports the following commands according to the Claude specification:

### 1. view

**Status:** ✅ Implemented

**Purpose:** Allows Claude to examine the contents of a file or list directory contents.

**Parameters:**
- `command`: Must be "view"
- `path`: The path to the file or directory to view
- `view_range` (optional): Array of two integers specifying start and end line numbers to view (1-indexed, -1 for end means read to the end of the file)

**Example for viewing a file:**
```json
{
  "command": "view",
  "path": "primes.py"
}
```

**Example for listing directory contents:**
```json
{
  "command": "view",
  "path": "/repo"
}
```

**Response format for files:**
```json
{
  "success": true,
  "is_directory": false,
  "content": "file contents as string",
  "message": "Successfully viewed file path"
}
```

**Response format for directories:**
```json
{
  "success": true,
  "is_directory": true,
  "content": "directory listing as string",
  "items": ["dir1/", "dir2/", "file1", "file2"],
  "message": "Successfully listed directory path"
}
```

### 2. str_replace

**Status:** ✅ Implemented

**Purpose:** Allows Claude to replace a specific string in a file with a new string.

**Parameters:**
- `command`: Must be "str_replace"
- `path`: The path to the file to modify
- `old_str`: The text to replace (must match exactly, including whitespace and indentation)
- `new_str`: The new text to insert in place of the old text

**Example:**
```json
{
  "command": "str_replace",
  "path": "primes.py",
  "old_str": "for num in range(2, limit + 1)",
  "new_str": "for num in range(2, limit + 1):"
}
```

### 3. create

**Status:** ✅ Implemented

**Purpose:** Allows Claude to create a new file with specified content.

**Parameters:**
- `command`: Must be "create"
- `path`: The path where the new file should be created
- `file_text`: The content to write to the new file

**Example:**
```json
{
  "command": "create",
  "path": "test_primes.py",
  "file_text": "import unittest\nimport primes\n\nclass TestPrimes(unittest.TestCase):\n    def test_is_prime(self):\n        self.assertTrue(primes.is_prime(2))\n        self.assertTrue(primes.is_prime(3))\n        self.assertFalse(primes.is_prime(4))\n\nif __name__ == '__main__':\n    unittest.main()"
}
```

### 4. insert

**Status:** ✅ Implemented

**Purpose:** Allows Claude to insert text at a specific location in a file.

**Parameters:**
- `command`: Must be "insert"
- `path`: The path to the file to modify
- `insert_line`: The line number after which to insert the text (0 for beginning of file)
- `new_str`: The text to insert

**Example:**
```json
{
  "command": "insert",
  "path": "primes.py",
  "insert_line": 0,
  "new_str": "\"\"\"Module for working with prime numbers.\n\nThis module provides functions to check if a number is prime\nand to generate a list of prime numbers up to a given limit.\n\"\"\"\n"
}
```

### 5. undo_edit

**Status:** ✅ Implemented

**Purpose:** Allows Claude to revert the last edit made to a file.

**Parameters:**
- `command`: Must be "undo_edit"
- `path`: The path to the file whose last edit should be undone

**Example:**
```json
{
  "command": "undo_edit",
  "path": "primes.py"
}
```

## Implementation Details

1. **Path Handling**:
   - ✅ Convert `/repo/` paths to local paths
   - ✅ Convert other absolute paths starting with `/` to relative paths
   - ✅ Handle relative and absolute paths correctly
   - ✅ Validate paths for security (prevent directory traversal)

2. **Error Handling**:
   - ✅ Return appropriate error messages for invalid commands or parameters
   - ✅ Handle file not found errors
   - ✅ Handle permission errors

3. **Undo Functionality**:
   - ✅ Implement a history mechanism to track changes to files
   - ✅ Store previous file contents for undo operations
   - ⚠️ Note: File history is stored in memory and is not persisted between different runs of the Janito CLI

4. **Response Format**:
   - ✅ Return consistent response format with success/failure status
   - ✅ Include appropriate error messages

## Testing

All commands have been tested and verified to work correctly:

1. **Standalone Testing**: A test script (`test_text_editor.py`) was created to test all commands directly.
2. **Integration Testing**: The tool was tested with the Janito CLI to ensure it works correctly with Claude.

## Limitations

1. The file history for undo operations is stored in memory and is not persisted between different runs of the Janito CLI.
2. The tool does not handle binary files, only text files.

## Future Improvements

1. Implement persistent file history for undo operations
2. Add more comprehensive error handling and validation
3. Add unit tests for all commands
4. Add support for binary files
