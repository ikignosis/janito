# Exit Codes

janito returns standard exit codes for scripting and automation.

## Exit Code Reference

| Code | Name | Description |
|------|------|-------------|
| `0` | Success | The command completed successfully |
| `1` | General Error | Configuration or runtime error |
| `130` | Interrupted | User cancelled with Ctrl+C |

## Detailed Explanations

### 0 - Success

The command completed successfully with no errors.

### 1 - General Error

An error occurred during execution. Common causes:

- Invalid configuration
- Missing API key
- API authentication failure
- Network connectivity issues
- Invalid arguments
- File operation errors
- Tool execution errors

### 130 - Interrupted (Ctrl+C)

The user cancelled the operation by pressing Ctrl+C. This is a standard Unix-style interrupt code.

## Checking Exit Codes

### Bash

```bash
janito "Hello"
echo "Exit code: $?"
```

### PowerShell

```powershell
janito "Hello"
Write-Host "Exit code: $LASTEXITCODE"
```

### Scripting Example

```bash
#!/bin/bash
janito "Your prompt"

if [ $? -eq 0 ]; then
    echo "Success!"
else
    echo "Failed with exit code: $?"
fi
```

## Error Handling Tips

1. **Always check exit codes** in scripts
2. **Enable logging** with `--log=debug` to diagnose errors
3. **Verify configuration** with `--show-config` before running
4. **Test connectivity** to API endpoints separately
