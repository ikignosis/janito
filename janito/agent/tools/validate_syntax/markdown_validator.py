from janito.i18n import tr
import re


def validate_markdown(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    errors = []
    for i, line in enumerate(content.splitlines(), 1):
        if re.match(r"^#+[^ #]", line):
            errors.append(f"Line {i}: Header missing space after # | {line.strip()}")
    if content.count("```") % 2 != 0:
        errors.append("Unclosed code block (```) detected")
    for i, line in enumerate(content.splitlines(), 1):
        if re.search(r"\[[^\]]*\]\([^)]+$", line):
            errors.append(
                f"Line {i}: Unclosed link or image (missing closing parenthesis) | {line.strip()}"
            )
    for i, line in enumerate(content.splitlines(), 1):
        if re.match(r"^([-*+])\1{1,}", line):
            continue
        if line.lstrip().startswith("|"):
            continue
        if re.match(r"^[-*+][^ \n]", line):
            stripped = line.strip()
            if not (
                stripped.startswith("*")
                and stripped.endswith("*")
                and len(stripped) > 2
            ):
                errors.append(
                    f"Line {i}: List item missing space after bullet | {line.strip()}"
                )
    if content.count("`") % 2 != 0:
        errors.append("Unclosed inline code (`) detected")
    if errors:
        msg = tr(
            "⚠️ Warning: Markdown syntax issues found:\n{errors}",
            errors="\n".join(errors),
        )
        return msg
    return "✅ Syntax valid"
