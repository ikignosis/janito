from janito.i18n import tr
import re


def validate_markdown(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    errors = []
    lines = content.splitlines()
    # Header space check
    for i, line in enumerate(lines, 1):
        if re.match(r"^#+[^ #]", line):
            errors.append(f"Line {i}: Header missing space after # | {line.strip()}")
    # Unclosed code block
    if content.count("```") % 2 != 0:
        errors.append("Unclosed code block (```) detected")
    # Unclosed link or image
    for i, line in enumerate(lines, 1):
        if re.search(r"\[[^\]]*\]\([^)]+$", line):
            errors.append(
                f"Line {i}: Unclosed link or image (missing closing parenthesis) | {line.strip()}"
            )
    # List item formatting and blank line before new list (bulleted and numbered)
    for i, line in enumerate(lines, 1):
        # Skip table lines
        if line.lstrip().startswith("|"):
            continue
        # List item missing space after bullet
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
        # Blank line before first item of a new bulleted list
        if re.match(r"^\s*[-*+] ", line):
            if i > 1:
                prev_line = lines[i - 2]
                prev_is_list = bool(re.match(r"^\s*[-*+] ", prev_line))
                if not prev_is_list and prev_line.strip() != "":
                    errors.append(
                        f"Line {i}: List should be preceded by a blank line for compatibility with MkDocs and other Markdown parsers | {line.strip()}"
                    )
        # Blank line before first item of a new numbered list
        if re.match(r"^\s*\d+\. ", line):
            if i > 1:
                prev_line = lines[i - 2]
                prev_is_numbered_list = bool(re.match(r"^\s*\d+\. ", prev_line))
                if not prev_is_numbered_list and prev_line.strip() != "":
                    errors.append(
                        f"Line {i}: Numbered list should be preceded by a blank line for compatibility with MkDocs and other Markdown parsers | {line.strip()}"
                    )
    # Unclosed inline code
    if content.count("`") % 2 != 0:
        errors.append("Unclosed inline code (`) detected")
    if errors:
        msg = tr(
            "⚠️ Warning: Markdown syntax issues found:\n{errors}",
            errors="\n".join(errors),
        )
        return msg
    return "✅ Syntax valid"
