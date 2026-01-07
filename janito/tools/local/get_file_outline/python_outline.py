import re
from typing import List


def handle_assignment(idx, assign_match, outline):
    var_name = assign_match.group(2)
    var_type = "const" if var_name.isupper() else "var"
    outline.append(
        {
            "type": var_type,
            "name": var_name,
            "start": idx + 1,
            "end": idx + 1,
            "parent": "",
            "docstring": "",
        }
    )


def handle_main(idx, outline):
    outline.append(
        {
            "type": "main",
            "name": "__main__",
            "start": idx + 1,
            "end": idx + 1,
            "parent": "",
            "docstring": "",
        }
    )


def close_stack_objects(idx, indent, stack, obj_ranges):
    while stack and indent < stack[-1][2]:
        popped = stack.pop()
        obj_ranges.append((popped[0], popped[1], popped[3], idx, popped[4], popped[2]))


def close_last_top_obj(idx, last_top_obj, stack, obj_ranges):
    if last_top_obj and last_top_obj in stack:
        stack.remove(last_top_obj)
        obj_ranges.append(
            (
                last_top_obj[0],
                last_top_obj[1],
                last_top_obj[3],
                idx,
                last_top_obj[4],
                last_top_obj[2],
            )
        )
        return None
    return last_top_obj


def handle_class(idx, class_match, indent, stack, last_top_obj):
    name = class_match.group(2)
    parent = stack[-1][1] if stack and stack[-1][0] == "class" else ""
    obj = ("class", name, indent, idx + 1, parent)
    stack.append(obj)
    if indent == 0:
        last_top_obj = obj
    return last_top_obj


def handle_function(idx, func_match, indent, stack, last_top_obj):
    name = func_match.group(2)
    parent = ""
    for s in reversed(stack):
        if s[0] == "class" and indent > s[2]:
            parent = s[1]
            break
    obj = ("function", name, indent, idx + 1, parent)
    stack.append(obj)
    if indent == 0:
        last_top_obj = obj
    return last_top_obj


def process_line(idx, line, regexes, stack, obj_ranges, outline, last_top_obj):
    class_pat, func_pat, assign_pat, main_pat = regexes
    class_match = class_pat.match(line)
    func_match = func_pat.match(line)
    assign_match = assign_pat.match(line)
    indent = len(line) - len(line.lstrip())
    # If a new top-level class or function starts, close the previous one
    if (class_match or func_match) and indent == 0 and last_top_obj:
        last_top_obj = close_last_top_obj(idx, last_top_obj, stack, obj_ranges)
    if class_match:
        last_top_obj = handle_class(idx, class_match, indent, stack, last_top_obj)
    elif func_match:
        last_top_obj = handle_function(idx, func_match, indent, stack, last_top_obj)
    elif assign_match and indent == 0:
        handle_assignment(idx, assign_match, outline)
    main_match = main_pat.match(line)
    if main_match:
        handle_main(idx, outline)
    close_stack_objects(idx, indent, stack, obj_ranges)
    return last_top_obj


def extract_signature_and_decorators(lines, start_idx):
    """
    Extracts the signature line and leading decorators for a given function/class/method.
    Returns (signature:str, decorators:List[str], signature_lineno:int)
    """
    decorators = []
    sig_line = None
    sig_lineno = start_idx
    for i in range(start_idx - 1, -1, -1):
        striped = lines[i].strip()
        if striped.startswith("@"):
            decorators.insert(0, striped)
            sig_lineno = i
        elif not striped:
            continue
        else:
            break
    # Find the signature line itself
    for k in range(start_idx, len(lines)):
        striped = lines[k].strip()
        if striped.startswith("def ") or striped.startswith("class "):
            sig_line = striped
            sig_lineno = k
            break
    return sig_line, decorators, sig_lineno


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


def build_outline_entry(obj, lines, outline):
    obj_type, name, start, end, parent, indent = obj
    # Determine if this is a method
    if obj_type == "function" and parent:
        outline_type = "method"
    elif obj_type == "function":
        outline_type = "function"
    else:
        outline_type = obj_type
    docstring = extract_docstring(lines, start, end)
    outline.append(
        {
            "type": outline_type,
            "name": name,
            "start": start,
            "end": end,
            "parent": parent,
            "docstring": docstring,
        }
    )


def process_lines(lines, regexes):
    outline = []
    stack = []
    obj_ranges = []
    last_top_obj = None
    for idx, line in enumerate(lines):
        last_top_obj = process_line(
            idx, line, regexes, stack, obj_ranges, outline, last_top_obj
        )
    # Close any remaining open objects
    for popped in stack:
        obj_ranges.append(
            (popped[0], popped[1], popped[3], len(lines), popped[4], popped[2])
        )
    return outline, obj_ranges


def build_outline(obj_ranges, lines, outline):
    for obj in obj_ranges:
        build_outline_entry(obj, lines, outline)
    return outline


def parse_python_outline(lines: List[str]):
    class_pat = re.compile(r"^(\s*)class\s+(\w+)")
    func_pat = re.compile(r"^(\s*)def\s+(\w+)")
    assign_pat = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=.*")
    main_pat = re.compile(r"^\s*if\s+__name__\s*==\s*[\'\"]__main__[\'\"]\s*:")
    outline = []
    stack = []
    obj_ranges = []
    last_top_obj = None
    for idx, line in enumerate(lines):
        class_match = class_pat.match(line)
        func_match = func_pat.match(line)
        assign_match = assign_pat.match(line)
        indent = len(line) - len(line.lstrip())
        parent = ""
        for s in reversed(stack):
            if s[0] == "class" and indent > s[2]:
                parent = s[1]
                break
        if class_match:
            obj = ("class", class_match.group(2), idx + 1, None, parent, indent)
            stack.append(obj)
            last_top_obj = obj
        elif func_match:
            obj = ("function", func_match.group(2), idx + 1, None, parent, indent)
            stack.append(obj)
            last_top_obj = obj
        elif assign_match and indent == 0:
            outline.append(
                {
                    "type": "const" if assign_match.group(2).isupper() else "var",
                    "name": assign_match.group(2),
                    "start": idx + 1,
                    "end": idx + 1,
                    "parent": "",
                    "signature": line.strip(),
                    "decorators": [],
                    "docstring": "",
                }
            )
        if line.strip().startswith("if __name__ == "):
            outline.append(
                {
                    "type": "main",
                    "name": "__main__",
                    "start": idx + 1,
                    "end": idx + 1,
                    "parent": "",
                    "signature": line.strip(),
                    "decorators": [],
                    "docstring": "",
                }
            )
        # Close stack objects if indent falls back
        while stack and indent <= stack[-1][5] and idx + 1 > stack[-1][2]:
            finished = stack.pop()
            outline_entry = finished[:2] + (
                finished[2],
                idx + 1,
                finished[4],
                finished[5],
            )
            build_outline_entry(outline_entry, lines, outline)
    # Close any remaining objects
    while stack:
        finished = stack.pop()
        outline_entry = finished[:2] + (
            finished[2],
            len(lines),
            finished[4],
            finished[5],
        )
        build_outline_entry(outline_entry, lines, outline)
    return outline

    class_pat = re.compile(r"^(\s*)class\s+(\w+)")
    func_pat = re.compile(r"^(\s*)def\s+(\w+)")
    assign_pat = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*=.*")
    main_pat = re.compile(r"^\s*if\s+__name__\s*==\s*[\'\"]__main__[\'\"]\s*:")
    regexes = (class_pat, func_pat, assign_pat, main_pat)
    outline, obj_ranges = process_lines(lines, regexes)
    return build_outline(obj_ranges, lines, outline)


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
