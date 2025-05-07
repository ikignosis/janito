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


def _get_validator(ext):
    """Return the appropriate validator function for the file extension."""
    mapping = {
        ".py": validate_python,
        ".pyw": validate_python,
        ".json": validate_json,
        ".yml": validate_yaml,
        ".yaml": validate_yaml,
        ".ps1": validate_ps1,
        ".xml": validate_xml,
        ".html": validate_html,
        ".htm": validate_html,
        ".md": validate_markdown,
        ".js": validate_js,
        ".css": validate_css,
    }
    return mapping.get(ext)


def _handle_validation_error(e, report_warning):
    msg = tr("\u26a0\ufe0f Warning: Syntax error: {error}", error=e)
    if report_warning:
        report_warning(msg)
    return msg


def validate_file_syntax(
    file_path: str, report_info=None, report_warning=None, report_success=None
) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    validator = _get_validator(ext)
    try:
        if validator:
            return validator(file_path)
        else:
            msg = tr("\u26a0\ufe0f Warning: Unsupported file extension: {ext}", ext=ext)
            if report_warning:
                report_warning(msg)
            return msg
    except Exception as e:
        return _handle_validation_error(e, report_warning)


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
            - "\u2705 Syntax OK"
            - "\u26a0\ufe0f Warning: Syntax error: <error message>"
            - "\u26a0\ufe0f Warning: Unsupported file extension: <ext>"
    """

    def run(self, file_path: str) -> str:
        disp_path = display_path(file_path)
        self.report_info(
            ActionType.READ,
            tr(
                "\U0001f50e Validate syntax for file '{disp_path}' ...",
                disp_path=disp_path,
            ),
        )
        result = validate_file_syntax(
            file_path,
            report_info=self.report_info,
            report_warning=self.report_warning,
            report_success=self.report_success,
        )
        if result.startswith("\u2705"):
            self.report_success(result)
        elif result.startswith("\u26a0\ufe0f"):
            self.report_warning(tr("\u26a0\ufe0f ") + result.lstrip("\u26a0\ufe0f "))
        return result
