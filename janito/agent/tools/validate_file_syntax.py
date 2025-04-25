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
      - PowerShell (.ps1)

    Args:
        file_path (str): Path to the file to validate.
    Returns:
        str: Validation status message. Example:
            - "✅ Syntax OK"
            - "⚠️ Warning: Syntax error: <error message>"
            - "⚠️ Warning: Unsupported file extension: <ext>"
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
            elif ext == ".ps1":

                from janito.agent.tools.run_powershell_command import (
                    RunPowerShellCommandTool,
                )

                ps_tool = RunPowerShellCommandTool()
                # Check if PSScriptAnalyzer is installed
                check_cmd = "if (Get-Command Invoke-ScriptAnalyzer -ErrorAction SilentlyContinue) { Write-Output 'PSScriptAnalyzerAvailable' } else { Write-Output 'PSScriptAnalyzerMissing' }"
                check_result = ps_tool.call(command=check_cmd, timeout=15)

                if "PSScriptAnalyzerMissing" in check_result:
                    msg = (
                        "⚠️ Warning: PSScriptAnalyzer is not installed. "
                        "For best PowerShell syntax validation, install it with:\n"
                        "    Install-Module -Name PSScriptAnalyzer -Scope CurrentUser\n"
                    )
                    self.report_warning(msg)
                    return msg
                # Run PSScriptAnalyzer
                analyze_cmd = f"Invoke-ScriptAnalyzer -Path '{file_path}' -Severity Error | ConvertTo-Json"
                analyze_result = ps_tool.call(command=analyze_cmd, timeout=30)

                if "[]" in analyze_result or analyze_result.strip() == "":
                    self.report_success("✅ Syntax OK")
                    return "✅ Syntax OK"
                else:
                    msg = (
                        f"⚠️ Warning: PowerShell syntax issues found:\n{analyze_result}"
                    )
                    self.report_warning(msg)
                    return msg
            else:
                msg = f"⚠️ Warning: Unsupported file extension: {ext}"
                self.report_warning(msg)
                return msg
            self.report_success("✅ Syntax OK")
            return "✅ Syntax OK"
        except Exception as e:
            msg = f"⚠️ Warning: Syntax error: {e}"
            self.report_warning(msg)
            return msg
