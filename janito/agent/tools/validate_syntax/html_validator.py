from janito.i18n import tr
import re


def validate_html(file_path: str) -> str:
    warnings = []
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    script_blocks = [
        m.span()
        for m in re.finditer(
            r"<script[\s\S]*?>[\s\S]*?<\/script>", html_content, re.IGNORECASE
        )
    ]
    js_patterns = [
        r"document\.addEventListener",
        r"^\s*(var|let|const)\s+\w+\s*[=;]",
        r"^\s*function\s+\w+\s*\(",
        r"^\s*(const|let|var)\s+\w+\s*=\s*\(.*\)\s*=>",
        r"^\s*window\.\w+\s*=",
        r"^\s*\$\s*\(",
    ]
    for pat in js_patterns:
        for m in re.finditer(pat, html_content):
            in_script = False
            for s_start, s_end in script_blocks:
                if s_start <= m.start() < s_end:
                    in_script = True
                    break
            if not in_script:
                warnings.append(
                    f"Line {html_content.count(chr(10), 0, m.start())+1}: JavaScript code ('{pat}') found outside <script> tag."
                )
    lxml_error = None
    try:
        from lxml import html

        with open(file_path, "rb") as f:
            html.parse(f)
        from lxml import etree

        parser = etree.HTMLParser(recover=False)
        with open(file_path, "rb") as f:
            etree.parse(f, parser=parser)
        if parser.error_log:
            errors = "\n".join(str(e) for e in parser.error_log)
            lxml_error = tr("HTML syntax errors found:\n{errors}", errors=errors)
    except ImportError:
        lxml_error = tr("⚠️ lxml not installed. Cannot validate HTML.")
    except Exception as e:
        lxml_error = tr("Syntax error: {error}", error=str(e))
    msg = ""
    if warnings:
        msg += (
            tr(
                "⚠️ Warning: JavaScript code found outside <script> tags. This is invalid HTML and will not execute in browsers.\n"
                + "\n".join(warnings)
            )
            + "\n"
        )
    if lxml_error:
        msg += lxml_error
    if msg:
        return msg.strip()
    return "✅ Syntax valid"
