# System Tools Plugin

## Overview

The System Tools plugin provides access to system-level operations and shell commands. This plugin enables interaction with the operating system, execution of shell commands, and system information retrieval.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|
| `run_powershell_command` | Execute PowerShell commands | Runs PowerShell commands on Windows systems with configurable timeout and confirmation |

## Usage Examples

### Running a System Command
```json
{
  "tool": "run_powershell_command",
  "command": "Get-Process | Where-Object {$_.CPU -gt 100}",
  "timeout": 30
}
```

### Checking Directory Contents
```json
{
  "tool": "run_powershell_command",
  "command": "Get-ChildItem -Path . -Recurse"
}
```

### System Information
```json
{
  "tool": "run_powershell_command",
  "command": "systeminfo | Select-String 'OS Name','OS Version'"
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
- Cross-platform command execution (Windows PowerShell)

This enables system-level automation while maintaining security boundaries and user control.