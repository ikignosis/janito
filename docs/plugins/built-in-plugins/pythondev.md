# Python Development Plugin

## Overview

The Python Development plugin provides tools for Python code execution and development. This plugin enables running Python code in various ways, supporting development, testing, and automation workflows.

## Resources Provided

### Tools

| Tool Name | Function | Description |
|-----------|----------|-------------|
| `python_code_run` | Execute Python code via stdin | Runs Python code by passing it to the interpreter via standard input |
| `python_command_run` | Execute Python with -c flag | Executes Python code using the `python -c` command-line flag |
| `python_file_run` | Run Python script files | Executes Python scripts from files with configurable timeout |

## Usage Examples

### Running Python Code
```json
{
  "tool": "python_code_run",
  "code": "print('Hello from Python!')\nfor i in range(3):\n    print(f'Iteration {i}')"
}
```

### Executing a One-liner
```json
{
  "tool": "python_command_run",
  "code": "import sys; print(f'Python {sys.version}')"
}
```

### Running a Script File
```json
{
  "tool": "python_file_run",
  "path": "scripts/data_processor.py",
  "timeout": 120
}
```

## Configuration

This plugin does not require any specific configuration. Python execution uses the system's default Python interpreter and environment.

## Security Considerations

- Code execution requires explicit user permission
- All Python operations are sandboxed and monitored
- Long-running scripts are automatically terminated based on timeout settings
- Access to system resources is controlled through Python's security model

## Integration

The Python Development plugin integrates with the code execution system to provide:

- Interactive Python development environment
- Automated testing and validation
- Script-based automation workflows
- Dynamic code generation and execution

This enables powerful Python-based automation while maintaining security boundaries and user control.