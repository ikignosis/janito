# Janito v3.5.1 Release Notes

**Release Date: August 29, 2025**

## Overview

Janito v3.5.1 is a patch release focused on improving user experience and reliability. This release adds comprehensive cancellation support to system and Python execution tools, allowing users to interrupt long-running operations gracefully.

## What's New

### 🚀 Cancellation Support

The biggest improvement in v3.5.1 is the addition of real-time cancellation support across all execution tools:

- **Bash Commands**: Cancel long-running shell commands with immediate feedback
- **Python Code**: Interrupt Python code execution without leaving hanging processes
- **Python Files**: Stop file execution mid-process with proper cleanup
- **Graceful Termination**: Clean process shutdown and resource cleanup
- **User Feedback**: Clear cancellation messages when operations are interrupted

### 🛠️ Terminal Output Improvements

- **Cleaner Output**: Removed styling from stdout/stderr for better readability
- **Tool Integration**: Improved compatibility with external tools and scripts
- **Copy-Paste Friendly**: Plain text output for easier copying and pasting

## Technical Details

### Enhanced Process Management
- Real-time cancellation event handling
- Proper thread cleanup and resource management
- Improved error handling for edge cases
- Better process lifecycle management

### Thread Safety
- Enhanced thread management for concurrent operations
- Safe cancellation handling across multiple threads
- Resource cleanup on cancellation

## Compatibility

This release maintains full backward compatibility with v3.5.0. All existing configurations and workflows continue to work without changes.

## Installation

### New Installation
```bash
pip install janito
```

### Upgrade from v3.5.0
```bash
pip install --upgrade janito
```

## Documentation

Updated documentation is available at: https://ikignosis.org/janito/

## Full Changelog

For a complete list of changes, see: [CHANGELOG.md](../CHANGELOG.md#351---2025-08-29)