from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
import os
import json

import yaml


@register_tool(name="validate_file_syntax")
class ValidateFileSyntaxTool(ToolBase):
    """
    Validate a file for syntax issues.

    Supported types:
      - Python (.py, .pyw)
      - JSON (.json)
      - YAML (.yml, .yaml)

    Args:
        file_path (str): Path to the file to validate.
    Returns:
        str: Validation status message. Example:
            - "✅ Syntax valid"
            - "Syntax error: <error message>"
            - "Error: <error message>"
    """

    def call(self, file_path: str) -> str:
        self.report_info(f"🔎 Validating syntax for: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext in [".py", ".pyw"]:
                import py_compile

                py_compile.compile(file_path, doraise=True)
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
            elif ext in [".yml", ".yaml"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    yaml.safe_load(f)
            else:
                msg = f"Error: Unsupported file extension: {ext}"
                self.report_error(msg)
                return msg
            self.report_success("✅ Syntax valid")
            return "✅ Syntax valid"
        except Exception as e:
            msg = f"Syntax error: {e}"
            self.report_error(msg)
            return msg
