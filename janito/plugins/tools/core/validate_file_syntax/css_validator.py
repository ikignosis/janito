from janito.i18n import tr
import re


def validate_css(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    errors = []
    # Check for unmatched curly braces
    if content.count("{") != content.count("}"):
        errors.append("Unmatched curly braces { }")
    # Check for unclosed comments
    if content.count("/*") != content.count("*/"):
        errors.append("Unclosed comment (/* ... */)")
    # Check for invalid property declarations (very basic)
    for i, line in enumerate(content.splitlines(), 1):
        # Ignore empty lines and comments
        if not line.strip() or line.strip().startswith("/*"):
            continue
        # Match property: value; (allow whitespace)
        if ":" in line and not re.search(r":.*;", line):
            errors.append(
                f"Line {i}: Missing semicolon after property value | {line.strip()}"
            )
        # Match lines with property but missing colon
        if ";" in line and ":" not in line:
            errors.append(
                f"Line {i}: Missing colon in property declaration | {line.strip()}"
            )
    if errors:
        msg = tr(
            "⚠️ Warning: CSS syntax issues found:\n{errors}", errors="\n".join(errors)
        )
        return msg
    return "✅ OK"
