import sys
import platform
import types
import pytest
from janito.agent.platform_discovery import PlatformDiscovery


def test_platform_name_and_python_version():
    pd = PlatformDiscovery()
    # Platform name should match normalized system
    sys_platform = platform.system().lower()
    expected = (
        "windows"
        if sys_platform.startswith("win")
        else (
            "linux"
            if sys_platform.startswith("linux")
            else "darwin" if sys_platform.startswith("darwin") else sys_platform
        )
    )
    assert pd.get_platform_name() == expected
    # Python version should match
    assert pd.get_python_version() == platform.python_version()


def test_is_windows_linux_mac():
    pd = PlatformDiscovery()
    assert pd.is_windows() == sys.platform.startswith("win")
    assert pd.is_linux() == sys.platform.startswith("linux")
    assert pd.is_mac() == sys.platform.startswith("darwin")


def test_detect_shell_runs_and_returns_str():
    pd = PlatformDiscovery()
    result = pd.detect_shell()
    assert isinstance(result, str)
    assert result  # Should not be empty
