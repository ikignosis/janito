from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
from janito.agent.tools_utils.utils import display_path
from janito.agent.tools.validate_syntax.validator import validate_file_syntax


@register_tool(name="validate_file_syntax")
class ValidateFileSyntaxTool(ToolBase):
    """
    Validate a file for syntax issues.

    Supported types:
      - Python (.py, .pyw)
      - JSON (.json)
      - YAML (.yml, .yaml)
      - PowerShell (.ps1)
      - XML (.xml)
      - HTML (.html, .htm) [lxml]
      - Markdown (.md)
      - JavaScript (.js)

    Args:
        file_path (str): Path to the file to validate.
    Returns:
        str: Validation status message. Example:
            - "✅ Syntax OK"
            - "⚠️ Warning: Syntax error: <error message>"
            - "⚠️ Warning: Unsupported file extension: <ext>"
    """

    def run(self, file_path: str) -> str:
        disp_path = display_path(file_path)
        self.report_info(
            tr("🔎 Validating syntax for file '{disp_path}' ...", disp_path=disp_path)
        )
        result = validate_file_syntax(
            file_path,
            report_info=self.report_info,
            report_warning=self.report_warning,
            report_success=self.report_success,
        )
        if result.startswith("✅"):
            self.report_success(result)
        elif result.startswith("⚠️"):
            self.report_warning(result)
        return result
