import os
import platform
import subprocess
import sys


class PlatformDiscovery:
    """
    Provides utilities for detecting the current shell, platform, and Python version.
    Uses the system's environment and subprocess modules internally.
    """

    def __init__(self):
        """
        Initialize the PlatformDiscovery instance.
        Uses os.environ and subprocess by default.
        """
        self.os_environ = os.environ
        self.subprocess_mod = subprocess

    def _detect_git_bash(self):
        if self.os_environ.get("MSYSTEM"):
            return f"Git Bash ({self.os_environ.get('MSYSTEM')})"
        return None

    def _detect_wsl(self):
        if self.os_environ.get("WSL_DISTRO_NAME"):
            shell = self.os_environ.get("SHELL")
            shell_name = shell.split("/")[-1] if shell else "unknown"
            distro = self.os_environ.get("WSL_DISTRO_NAME")
            return f"{shell_name} (WSL: {distro})"
        return None

    def _detect_powershell(self):
        try:
            result = self.subprocess_mod.run(
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

    def _detect_shell_env(self):
        shell = self.os_environ.get("SHELL")
        if shell:
            return shell
        return None

    def _detect_comspec(self):
        comspec = self.os_environ.get("COMSPEC")
        if comspec:
            if "powershell" in comspec.lower():
                return "PowerShell"
            elif "cmd" in comspec.lower():
                return "cmd.exe"
            else:
                return "Unknown shell"
        return "Unknown shell"

    def _append_term_info(self, shell_info):
        term_env = self.os_environ.get("TERM")
        if term_env:
            shell_info += f" [TERM={term_env}]"
        term_program = self.os_environ.get("TERM_PROGRAM")
        if term_program:
            shell_info += f" [TERM_PROGRAM={term_program}]"
        return shell_info

    def detect_shell(self) -> str:
        """
        Detects the current shell environment and returns a descriptive string,
        including terminal information if available.

        Note:
            This method may invoke subprocesses to execute shell commands
            (e.g., to detect PowerShell), which could have side effects or
            performance implications.

        Returns:
            str: Description of the detected shell and terminal info.
        """
        shell_info = (
            self._detect_git_bash()
            or self._detect_wsl()
            or self._detect_powershell()
            or self._detect_shell_env()
            or self._detect_comspec()
        )
        shell_info = self._append_term_info(shell_info)
        return shell_info

    def get_platform_name(self) -> str:
        """
        Returns the normalized platform name.

        Returns:
            str: One of 'windows', 'linux', 'darwin', or the raw platform string.
        """
        sys_platform = platform.system().lower()
        if sys_platform.startswith("win"):
            return "windows"
        elif sys_platform.startswith("linux"):
            return "linux"
        elif sys_platform.startswith("darwin"):
            return "darwin"
        return sys_platform

    def get_python_version(self) -> str:
        """
        Returns the current Python version as a string.

        Returns:
            str: Python version (e.g., '3.12.0').
        """
        return platform.python_version()

    def is_windows(self) -> bool:
        """
        Checks if the current platform is Windows.

        Returns:
            bool: True if running on Windows, False otherwise.
        """
        return sys.platform.startswith("win")

    def is_linux(self) -> bool:
        """
        Checks if the current platform is Linux.

        Returns:
            bool: True if running on Linux, False otherwise.
        """
        return sys.platform.startswith("linux")

    def is_mac(self) -> bool:
        """
        Checks if the current platform is macOS.

        Returns:
            bool: True if running on macOS, False otherwise.
        """
        return sys.platform.startswith("darwin")
