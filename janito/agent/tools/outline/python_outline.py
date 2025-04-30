outline = []
stack = []  # (type, name, indent, start, parent)


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
