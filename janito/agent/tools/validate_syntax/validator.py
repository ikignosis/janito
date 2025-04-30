import os
from janito.i18n import tr

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
