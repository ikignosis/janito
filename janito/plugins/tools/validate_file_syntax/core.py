import os
from janito.tools.path_utils import expand_path
from janito.i18n import tr
from janito.tools.tool_base import ToolBase, ToolPermissions
from janito.report_events import ReportAction
from janito.tools.adapters.local.adapter import register_local_tool
from janito.tools.tool_utils import display_path
from janito.plugins.tools.decorators import register_core_tool as register_tool

from .python_validator import validate_python
from .json_validator import validate_json
from .yaml_validator import validate_yaml
from .ps1_validator import validate_ps1
from .xml_validator import validate_xml
from .html_validator import validate_html
from .markdown_validator import validate_markdown
from .js_validator import validate_js
from .css_validator import validate_css
from .jinja2_validator import validate_jinja2
from janito.tools.loop_protection_decorator import protect_against_loops


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
        ".j2": validate_jinja2,
        ".jinja2": validate_jinja2,
    }
    return mapping.get(ext)


def _handle_validation_error(e, report_warning):
    msg = tr("⚠️ Warning: Syntax error: {error}", error=e)
    if report_warning:
        report_warning(msg)
    return msg


def validate_file_syntax(
    path: str, report_info=None, report_warning=None, report_success=None
) -> str:
    ext = os.path.splitext(path)[1].lower()
    validator = _get_validator(ext)
    try:
        if validator:
            return validator(path)
        else:
            msg = tr("⚠️ Warning: Unsupported file extension: {ext}", ext=ext)
            if report_warning:
                report_warning(msg)
            return msg
    except Exception as e:
        return _handle_validation_error(e, report_warning)


class ValidateFileSyntax(ToolBase):
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
      - Jinja2 templates (.j2, .jinja2)

    Args:
        path (str): Path to the file to validate.
    Returns:
        str: Validation status message. Example:
            - "✅ Syntax OK"
            - "⚠️ Warning: Syntax error: <error message>"
            - "⚠️ Warning: Unsupported file extension: <ext>"
    """

    permissions = ToolPermissions(read=True)
    tool_name = "validate_file_syntax"

    @protect_against_loops(max_calls=5, time_window=10.0, key_field="path")
    def run(self, path: str) -> str:
        path = expand_path(path)
        disp_path = display_path(path)
        self.report_action(
            tr(
                "🔎 Validate syntax for file '{disp_path}' ...",
                disp_path=disp_path,
            ),
            ReportAction.READ,
        )
        result = validate_file_syntax(
            path,
            report_warning=self.report_warning,
            report_success=self.report_success,
        )
        if result.startswith("✅"):
            self.report_success(result, ReportAction.READ)

        return result
