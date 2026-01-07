from janito.i18n import tr
import re


def validate_js(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    errors = []
    if content.count("{") != content.count("}"):
        errors.append("Unmatched curly braces { }")
    if content.count("(") != content.count(")"):
        errors.append("Unmatched parentheses ( )")
    if content.count("[") != content.count("]"):
        errors.append("Unmatched brackets [ ]")
    for quote in ["'", '"', "`"]:
        unescaped = re.findall(rf"(?<!\\){quote}", content)
        if len(unescaped) % 2 != 0:
            errors.append(f"Unclosed string literal ({quote}) detected")
    if content.count("/*") != content.count("*/"):
        errors.append("Unclosed block comment (/* ... */)")
    if errors:
        msg = tr(
            "⚠️ Warning: JavaScript syntax issues found:\n{errors}",
            errors="\n".join(errors),
        )
        return msg
    return "✅ OK"
