# System Tools Plugin

## Overview

The System Tools plugin provides access to system-level operations and shell commands. This plugin enables interaction with the operating system, execution of shell commands, and system information retrieval.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|
| `run_bash_command` | Execute bash commands | Runs bash shell commands on Linux, macOS, and Windows (with bash available) with live output streaming |
| `run_powershell_command` | Execute PowerShell commands | Runs PowerShell commands on Windows and cross-platform (PowerShell Core) with configurable timeout and confirmation |

## Usage Examples

### Running Bash Commands
```json
{
  "tool": "run_bash_command",
  "command": "ls -la | grep '.py'",
  "timeout": 30
}
```

### Running PowerShell Commands
```json
{
  "tool": "run_powershell_command",
  "command": "Get-Process | Where-Object {$_.CPU -gt 100}",
  "timeout": 30
}
```

### Checking Directory Contents (Bash)
```json
{
  "tool": "run_bash_command",
  "command": "find . -name '*.txt' -type f"
}
```

### Checking Directory Contents (PowerShell)
```json
{
  "tool": "run_powershell_command",
  "command": "Get-ChildItem -Path . -Recurse"
}
```

### System Information (Bash)
```json
{
  "tool": "run_bash_command",
  "command": "uname -a && df -h"
}
```

### System Information (PowerShell)
```json
{
  "tool": "run_powershell_command",
  "command": "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion"
}
```

## Configuration

This plugin does not require any specific configuration. The command execution respects the user's system permissions and security policies.

## Security Considerations

- Command execution requires explicit user permission
- Commands are sandboxed and monitored for potentially harmful operations
- Long-running commands are automatically terminated based on timeout settings
- Sensitive system commands may require additional authentication

## Integration

The System Tools plugin integrates with the terminal interface to provide:

- Direct access to system utilities
- Automation of system administration tasks
- Environment inspection for debugging purposes
- Cross-platform command execution (Bash on Unix-like systems, PowerShell on Windows and cross-platform)

This enables system-level automation while maintaining security boundaries and user control.