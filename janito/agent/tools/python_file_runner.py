import subprocess
import sys
from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.i18n import tr


@register_tool(name="python_file_runner")
class PythonFileRunnerTool(ToolBase):
    """
    Tool to execute a specified Python script file.
    Args:
        file_path (str): Path to the Python script file to execute.
        timeout (int, optional): Timeout in seconds for the command. Defaults to 60.
    Returns:
        str: Output and status message.
    """

    def run(self, file_path: str, timeout: int = 60) -> str:
        self.report_info(
            ActionType.EXECUTE,
            tr("🐍 Running: python {file_path}", file_path=file_path),
        )
        try:
            result = subprocess.run(
                [sys.executable, file_path],
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
            return tr("Error running file: {error}", error=e)
