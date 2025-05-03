import os
from janito.i18n import tr
from janito.agent.tool_base import ToolBase
from janito.agent.tools_utils.action_type import ActionType
from janito.agent.tool_registry import register_tool
from janito.agent.tools_utils.utils import display_path

from .python_validator import validate_python
from .json_validator import validate_json
from .yaml_validator import validate_yaml
from .ps1_validator import validate_ps1
from .xml_validator import validate_xml
from .html_validator import validate_html
from .markdown_validator import validate_markdown
from .js_validator import validate_js
from .css_validator import validate_css


def validate_file_syntax(
    file_path: str, report_info=None, report_warning=None, report_success=None
) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext in [".py", ".pyw"]:
            return validate_python(file_path)
        elif ext == ".json":
            return validate_json(file_path)
        elif ext in [".yml", ".yaml"]:
            return validate_yaml(file_path)
        elif ext == ".ps1":
            return validate_ps1(file_path)
        elif ext == ".xml":
            return validate_xml(file_path)
        elif ext in (".html", ".htm"):
            return validate_html(file_path)
        elif ext == ".md":
            return validate_markdown(file_path)
        elif ext == ".js":
            return validate_js(file_path)
        elif ext == ".css":
            return validate_css(file_path)
        else:
            msg = tr("⚠️ Warning: Unsupported file extension: {ext}", ext=ext)
            if report_warning:
                report_warning(msg)
            return msg
    except Exception as e:
        msg = tr("⚠️ Warning: Syntax error: {error}", error=e)
        if report_warning:
            report_warning(msg)
        return msg


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
            ActionType.READ,
            tr("🔎 Validating syntax for file '{disp_path}' ...", disp_path=disp_path),
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
            self.report_warning(tr("⚠️ ") + result.lstrip("⚠️ "))
        return result
