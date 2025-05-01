import re
from typing import List


def parse_python_outline(lines: List[str]):
    class_pat = re.compile(r"^(\s*)class\s+(\w+)")
    func_pat = re.compile(r"^(\s*)def\s+(\w+)")
    assign_pat = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=.*")
    main_pat = re.compile(r"^\s*if\s+__name__\s*==\s*[\'\"]__main__[\'\"]\s*:")
    outline = []
    stack = []  # (type, name, indent, start, parent)
    for idx, line in enumerate(lines):
        class_match = class_pat.match(line)
        func_match = func_pat.match(line)
        assign_match = assign_pat.match(line)
        indent = len(line) - len(line.lstrip())
        if class_match:
            name = class_match.group(2)
            parent = stack[-1][1] if stack and stack[-1][0] == "class" else ""
            stack.append(("class", name, indent, idx + 1, parent))
        elif func_match:
            name = func_match.group(2)
            parent = (
                stack[-1][1]
                if stack
                and stack[-1][0] in ("class", "function")
                and indent > stack[-1][2]
                else ""
            )
            stack.append(("function", name, indent, idx + 1, parent))
        elif assign_match and indent == 0:
            var_name = assign_match.group(2)
            var_type = "const" if var_name.isupper() else "var"
            outline.append(
                {
                    "type": var_type,
                    "name": var_name,
                    "start": idx + 1,
                    "end": idx + 1,
                    "parent": "",
                }
            )
        main_match = main_pat.match(line)
        if main_match:
            outline.append(
                {
                    "type": "main",
                    "name": "__main__",
                    "start": idx + 1,
                    "end": idx + 1,
                    "parent": "",
                }
            )
        while stack and indent < stack[-1][2]:
            popped = stack.pop()
            outline.append(
                {
                    "type": (
                        popped[0]
                        if popped[0] != "function" or popped[3] == 1
                        else ("method" if popped[4] else "function")
                    ),
                    "name": popped[1],
                    "start": popped[3],
                    "end": idx,
                    "parent": popped[4],
                }
            )
    for popped in stack:
        outline.append(
            {
                "type": (
                    popped[0]
                    if popped[0] != "function" or popped[3] == 1
                    else ("method" if popped[4] else "function")
                ),
                "name": popped[1],
                "start": popped[3],
                "end": len(lines),
                "parent": popped[4],
            }
        )
    return outline


def extract_docstring(lines, start_idx, end_idx):
    """Extracts a docstring from lines[start_idx:end_idx] if present."""
    for i in range(start_idx, min(end_idx, len(lines))):
        line = lines[i].lstrip()
        if not line:
            continue
        if line.startswith('"""') or line.startswith("'''"):
            quote = line[:3]
            doc = line[3:]
            if doc.strip().endswith(quote):
                return doc.strip()[:-3].strip()
            docstring_lines = [doc]
            for j in range(i + 1, min(end_idx, len(lines))):
                line = lines[j]
                if line.strip().endswith(quote):
                    docstring_lines.append(line.strip()[:-3])
                    return "\n".join([d.strip() for d in docstring_lines]).strip()
                docstring_lines.append(line)
            break
        else:
            break
    return ""
