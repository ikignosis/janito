"""
Python Development Plugin

Python development and execution tools.
"""

from typing import Optional


def python_code_run(code: str, timeout: int = 60) -> str:
    """Execute Python code via stdin"""
    return f"python_code_run(code='{len(code)} chars', timeout={timeout})"


python_code_run.tool_name = "python_code_run"


def python_command_run(code: str, timeout: int = 60) -> str:
    """Execute Python with -c flag"""
    return f"python_command_run(code='{len(code)} chars', timeout={timeout})"


python_command_run.tool_name = "python_command_run"


def python_file_run(path: str, timeout: int = 60) -> str:
    """Run Python script files"""
    return f"python_file_run(path='{path}', timeout={timeout})"


python_file_run.tool_name = "python_file_run"


# Plugin metadata
__plugin_name__ = "dev.pythondev"
__plugin_description__ = "Python development and execution"
__plugin_tools__ = [python_code_run, python_command_run, python_file_run]
