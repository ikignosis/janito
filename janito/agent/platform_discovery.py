import platform
import sys


def _detect_git_bash(os_environ):
    if os_environ.get("MSYSTEM"):
        return f"Git Bash ({os_environ.get('MSYSTEM')})"
    return None


def _detect_wsl(os_environ):
    if os_environ.get("WSL_DISTRO_NAME"):
        shell = os_environ.get("SHELL")
        shell_name = shell.split("/")[-1] if shell else "unknown"
        distro = os_environ.get("WSL_DISTRO_NAME")
        return f"{shell_name} (WSL: {distro})"
    return None


def _detect_powershell(subprocess_mod):
    try:
        result = subprocess_mod.run(
            ["powershell.exe", "-NoProfile", "-Command", "$host.Name"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and "ConsoleHost" in result.stdout:
            return "PowerShell"
    except Exception:
        pass
    return None


def _detect_shell_env(os_environ):
    shell = os_environ.get("SHELL")
    if shell:
        return shell
    return None


def _detect_comspec(os_environ):
    comspec = os_environ.get("COMSPEC")
    if comspec:
        if "powershell" in comspec.lower():
            return "PowerShell"
        elif "cmd" in comspec.lower():
            return "cmd.exe"
        else:
            return "Unknown shell"
    return "Unknown shell"


def _append_term_info(shell_info, os_environ):
    term_env = os_environ.get("TERM")
    if term_env:
        shell_info += f" [TERM={term_env}]"
    term_program = os_environ.get("TERM_PROGRAM")
    if term_program:
        shell_info += f" [TERM_PROGRAM={term_program}]"
    return shell_info


def detect_shell():
    import os
    import subprocess

    shell_info = (
        _detect_git_bash(os.environ)
        or _detect_wsl(os.environ)
        or _detect_powershell(subprocess)
        or _detect_shell_env(os.environ)
        or _detect_comspec(os.environ)
    )
    shell_info = _append_term_info(shell_info, os.environ)
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
