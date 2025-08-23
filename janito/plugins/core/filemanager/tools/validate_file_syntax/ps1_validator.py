from janito.i18n import tr
import re


def validate_ps1(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    errors = []
    # Unmatched curly braces
    if content.count("{") != content.count("}"):
        errors.append("Unmatched curly braces { }")
    # Unmatched parentheses
    if content.count("(") != content.count(")"):
        errors.append("Unmatched parentheses ( )")
    # Unmatched brackets
    if content.count("[") != content.count("]"):
        errors.append("Unmatched brackets [ ]")
    # Unclosed string literals
    for quote in ["'", '"']:
        unescaped = re.findall(rf"(?<!\\){quote}", content)
        if len(unescaped) % 2 != 0:
            errors.append(f"Unclosed string literal ({quote}) detected")
    # Unclosed block comments <# ... #>
    if content.count("<#") != content.count("#>"):
        errors.append("Unclosed block comment (<# ... #>)")
    if errors:
        msg = tr(
            "⚠️ Warning: PowerShell syntax issues found:\n{errors}",
            errors="\n".join(errors),
        )
        return msg
    return "✅ OK"
