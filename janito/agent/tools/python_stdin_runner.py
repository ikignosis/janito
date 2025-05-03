import subprocess
import sys
from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.i18n import tr


@register_tool(name="python_stdin_runner")
class PythonStdinRunnerTool(ToolBase):
    """
    Tool to execute Python code by passing it to the interpreter via standard input (stdin).
    Args:
        code (str): The Python code to execute as a string.
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
    Returns:
        str: Output and status message.
    """

    def run(self, code: str, timeout: int = 60) -> str:
        if not code.strip():
            self.report_warning(tr("ℹ️ Empty code provided."))
            return tr("Warning: Empty code provided. Operation skipped.")
        self.report_info(
            ActionType.EXECUTE,
            tr("🐍 Running: python (stdin mode) ...\n{code}\n", code=code),
        )
        try:
            result = subprocess.run(
                [sys.executable],
                input=code,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**dict(), **dict(PYTHONIOENCODING="utf-8")},
            )
            self.report_success(
                tr("✅ Return code {returncode}", returncode=result.returncode)
            )
            output = (
                f"Return code: {result.returncode}\n--- STDOUT ---\n{result.stdout}"
            )
            if result.stderr.strip():
                output += f"\n--- STDERR ---\n{result.stderr}"
            return output
        except subprocess.TimeoutExpired:
            self.report_error(
                tr("❌ Timed out after {timeout} seconds.", timeout=timeout)
            )
            return tr("Code timed out after {timeout} seconds.", timeout=timeout)
        except Exception as e:
            self.report_error(tr("❌ Error: {error}", error=e))
            return tr("Error running code via stdin: {error}", error=e)
