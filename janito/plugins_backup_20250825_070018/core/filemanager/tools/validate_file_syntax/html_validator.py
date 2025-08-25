from janito.i18n import tr
import re

try:
    from lxml import etree
except ImportError:
    etree = None


def validate_html(path: str) -> str:
    html_content = _read_html_content(path)
    warnings = _find_js_outside_script(html_content)
    lxml_error = _parse_html_and_collect_errors(path)
    msg = _build_result_message(warnings, lxml_error)
    return msg


def _read_html_content(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _find_js_outside_script(html_content):
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
    warnings = []
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
    return warnings


def _parse_html_and_collect_errors(path):
    lxml_error = None
    if etree is None:
        lxml_error = tr("⚠️ lxml not installed. Cannot validate HTML.")
        return lxml_error
    try:
        parser = etree.HTMLParser(recover=False)
        with open(path, "rb") as f:
            etree.parse(f, parser=parser)
        error_log = parser.error_log
        syntax_errors = []
        for e in error_log:
            if (
                "mismatch" in e.message.lower()
                or "tag not closed" in e.message.lower()
                or "unexpected end tag" in e.message.lower()
                or "expected" in e.message.lower()
            ):
                syntax_errors.append(str(e))
        if syntax_errors:
            lxml_error = tr("Syntax error: {error}", error="; ".join(syntax_errors))
        elif error_log:
            lxml_error = tr(
                "HTML syntax errors found:\n{errors}",
                errors="\n".join(str(e) for e in error_log),
            )
    except ImportError:
        lxml_error = tr("⚠️ lxml not installed. Cannot validate HTML.")
    except Exception as e:
        lxml_error = tr("Syntax error: {error}", error=str(e))
    return lxml_error


def _build_result_message(warnings, lxml_error):
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
    return "✅ OK"
