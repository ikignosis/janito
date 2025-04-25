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
      - XML (.xml)
      - HTML (.html, .htm) [lxml]

    Args:
        file_path (str): Path to the file to validate.
    Returns:
        str: Validation status message. Example:
            - "✅ Syntax OK"
            - "⚠️ Warning: Syntax error: <error message>"
            - "⚠️ Warning: Unsupported file extension: <ext>"
    """

    def call(self, file_path: str) -> str:
        self.report_info(f"🔎 Validating syntax for: {file_path} ...")
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
                    return "✅ Syntax valid"
                else:
                    msg = (
                        f"⚠️ Warning: PowerShell syntax issues found:\n{analyze_result}"
                    )
                    self.report_warning(msg)
                    return msg
            elif ext == ".xml":
                try:
                    from lxml import etree
                except ImportError:
                    msg = "⚠️ lxml not installed. Cannot validate XML."
                    self.report_warning(msg)
                    return msg
                with open(file_path, "rb") as f:
                    etree.parse(f)
            elif ext in (".html", ".htm"):
                try:
                    from lxml import html
                except ImportError:
                    msg = "⚠️ lxml not installed. Cannot validate HTML."
                    self.report_warning(msg)
                    return msg
                with open(file_path, "rb") as f:
                    html.parse(f)
                    # Strict: check for unclosed tags and mismatches
                    # lxml.html will not raise for some malformed HTML, so check for parser errors
                    # We use etree.HTMLParser with recover=False for strictness
                from lxml import etree

                parser = etree.HTMLParser(recover=False)
                with open(file_path, "rb") as f:
                    etree.parse(f, parser=parser)
                if parser.error_log:
                    errors = "\n".join(str(e) for e in parser.error_log)
                    raise ValueError(f"HTML syntax errors found:\n{errors}")
            else:
                msg = f"⚠️ Warning: Unsupported file extension: {ext}"
                self.report_warning(msg)
                return msg
            self.report_success("✅ Syntax OK")
            return "✅ Syntax valid"
        except Exception as e:
            msg = f"⚠️ Warning: Syntax error: {e}"
            self.report_warning(msg)
            return msg
