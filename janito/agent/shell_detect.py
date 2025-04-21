def detect_shell():
    import os
    import subprocess

    # Try to detect PowerShell by running $host.Name
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "$host.Name"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and "ConsoleHost" in result.stdout:
            shell_info = "PowerShell"
        else:
            shell_info = None
    except Exception:
        shell_info = None

    if not shell_info:
        shell = os.environ.get("SHELL")
        if shell:
            shell_info = shell
        elif os.environ.get("MSYSTEM"):
            shell_info = f"Git Bash ({os.environ.get('MSYSTEM')})"
        elif os.environ.get("WSL_DISTRO_NAME"):
            shell_info = f"WSL ({os.environ.get('WSL_DISTRO_NAME')})"
        else:
            comspec = os.environ.get("COMSPEC")
            if comspec:
                if "powershell" in comspec.lower():
                    shell_info = "PowerShell"
                elif "cmd" in comspec.lower():
                    shell_info = "cmd.exe"
                else:
                    shell_info = "Unknown shell"
            else:
                shell_info = "Unknown shell"

    # VSCode detection
    term_program = os.environ.get("TERM_PROGRAM")
    if term_program and term_program.lower() == "vscode":
        shell_info += ", running in VSCode"

    return shell_info
