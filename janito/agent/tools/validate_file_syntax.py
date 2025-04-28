from janito.agent.tool_base import ToolBase
from janito.agent.tool_registry import register_tool
from janito.i18n import tr
import os
import json
import yaml
from janito.agent.tools.utils import display_path


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

    def run(self, file_path: str) -> str:
        disp_path = display_path(file_path)
        self.report_info(
            tr("🔎 Validating syntax for: {disp_path} ...", disp_path=disp_path)
        )
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
                check_cmd = "if (Get-Command Invoke-ScriptAnalyzer -ErrorAction SilentlyContinue) { Write-Output 'PSScriptAnalyzerAvailable' } else { Write-Output 'PSScriptAnalyzerMissing' }"
                check_result = ps_tool.run(command=check_cmd, timeout=15)
                if "PSScriptAnalyzerMissing" in check_result:
                    msg = tr(
                        "⚠️ Warning: PSScriptAnalyzer is not installed. For best PowerShell syntax validation, install it with:\n    Install-Module -Name PSScriptAnalyzer -Scope CurrentUser\n"
                    )
                    self.report_warning(msg)
                    return msg
                analyze_cmd = f"Invoke-ScriptAnalyzer -Path '{file_path}' -Severity Error | ConvertTo-Json"
                analyze_result = ps_tool.run(command=analyze_cmd, timeout=30)
                if "[]" in analyze_result or analyze_result.strip() == "":
                    self.report_success(tr("✅ Syntax OK"))
                    return tr("✅ Syntax valid")
                else:
                    msg = tr(
                        "⚠️ Warning: PowerShell syntax issues found:\n{analyze_result}",
                        analyze_result=analyze_result,
                    )
                    self.report_warning(msg)
                    return msg
            elif ext == ".xml":
                try:
                    from lxml import etree
                except ImportError:
                    msg = tr("⚠️ lxml not installed. Cannot validate XML.")
                    self.report_warning(msg)
                    return msg
                with open(file_path, "rb") as f:
                    etree.parse(f)
            elif ext in (".html", ".htm"):
                try:
                    from lxml import html
                except ImportError:
                    msg = tr("⚠️ lxml not installed. Cannot validate HTML.")
                    self.report_warning(msg)
                    return msg
                with open(file_path, "rb") as f:
                    html.parse(f)
                from lxml import etree

                parser = etree.HTMLParser(recover=False)
                with open(file_path, "rb") as f:
                    etree.parse(f, parser=parser)
                if parser.error_log:
                    errors = "\n".join(str(e) for e in parser.error_log)
                    raise ValueError(
                        tr("HTML syntax errors found:\n{errors}", errors=errors)
                    )
            elif ext == ".md":
                import re

                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                errors = []
                # Rule: Headers must start with # followed by a space
                for i, line in enumerate(content.splitlines(), 1):
                    if re.match(r"^#+[^ #]", line):
                        errors.append(
                            f"Line {i}: Header missing space after # | {line.strip()}"
                        )
                # Rule: Unclosed code blocks
                if content.count("```") % 2 != 0:
                    errors.append("Unclosed code block (```) detected")
                # Rule: Unclosed links/images (flag only if line contains [text]( but not ))
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(r"\[[^\]]*\]\([^)]+$", line):
                        errors.append(
                            f"Line {i}: Unclosed link or image (missing closing parenthesis) | {line.strip()}"
                        )
                # Rule: List items must start with -, *, or + followed by space
                for i, line in enumerate(content.splitlines(), 1):
                    # Skip horizontal rules like --- or ***
                    if re.match(r"^([-*+])\1{1,}", line):
                        continue
                    # Skip table rows (lines starting with |)
                    if line.lstrip().startswith("|"):
                        continue
                    # Only flag as list item if there is text after the bullet (not just emphasis)
                    if re.match(r"^[-*+][^ \n]", line):
                        stripped = line.strip()
                        # If the line is surrounded by * and ends with *, it's likely emphasis, not a list
                        if not (
                            stripped.startswith("*")
                            and stripped.endswith("*")
                            and len(stripped) > 2
                        ):
                            errors.append(
                                f"Line {i}: List item missing space after bullet | {line.strip()}"
                            )
                # Rule: Inline code must have even number of backticks
                if content.count("`") % 2 != 0:
                    errors.append("Unclosed inline code (`) detected")
                if errors:
                    msg = tr(
                        "⚠️ Warning: Markdown syntax issues found:\n{errors}",
                        errors="\n".join(errors),
                    )
                    self.report_warning(msg)
                    return msg
            else:
                msg = tr("⚠️ Warning: Unsupported file extension: {ext}", ext=ext)
                self.report_warning(msg)
                return msg
            self.report_success(tr("✅ Syntax OK"))
            return tr("✅ Syntax valid")
        except Exception as e:
            msg = tr("⚠️ Warning: Syntax error: {error}", error=e)
            self.report_warning(msg)
            return msg
