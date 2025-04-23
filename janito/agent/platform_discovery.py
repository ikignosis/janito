import platform
import sys


def detect_shell():
    import os
    import subprocess

    shell_info = None

    # 1. Detect shell (prefer Git Bash if detected)
    if os.environ.get("MSYSTEM"):
        shell_info = f"Git Bash ({os.environ.get('MSYSTEM')})"
    # 2. Detect WSL (before PowerShell)
    elif os.environ.get("WSL_DISTRO_NAME"):
        shell = os.environ.get("SHELL")
        shell_name = shell.split("/")[-1] if shell else "unknown"
        distro = os.environ.get("WSL_DISTRO_NAME")
        shell_info = f"{shell_name} (WSL: {distro})"
    else:
        # 3. Try to detect PowerShell by running $host.Name
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

        # 4. If not PowerShell, check SHELL
        if not shell_info:
            shell = os.environ.get("SHELL")
            if shell:
                shell_info = shell
            else:
                # 5. If not, check COMSPEC for PowerShell or cmd.exe
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

    # 6. Always append TERM and TERM_PROGRAM if present
    term_env = os.environ.get("TERM")
    if term_env:
        shell_info += f" [TERM={term_env}]"

    term_program = os.environ.get("TERM_PROGRAM")
    if term_program:
        shell_info += f" [TERM_PROGRAM={term_program}]"

    return shell_info


def get_platform_name():
    sys_platform = platform.system().lower()
    if sys_platform.startswith("win"):
        return "windows"
    elif sys_platform.startswith("linux"):
        return "linux"
    elif sys_platform.startswith("darwin"):
        return "darwin"
    return sys_platform


def get_python_version():
    return platform.python_version()


def is_windows():
    return sys.platform.startswith("win")


def is_linux():
    return sys.platform.startswith("linux")


def is_mac():
    return sys.platform.startswith("darwin")
