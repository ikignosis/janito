def format_outline_table(outline_items):
    if not outline_items:
        return "No classes, functions, or variables found."
    header = "| Type    | Name        | Start | End | Parent   | Docstring                |\n|---------|-------------|-------|-----|----------|--------------------------|"
    rows = []
    for item in outline_items:
        docstring = item.get("docstring", "").replace("\n", " ")
        if len(docstring) > 24:
            docstring = docstring[:21] + "..."
        rows.append(
            f"| {item['type']:<7} | {item['name']:<11} | {item['start']:<5} | {item['end']:<3} | {item['parent']:<8} | {docstring:<24} |"
        )
    return header + "\n" + "\n".join(rows)


def format_markdown_outline_table(outline_items):
    if not outline_items:
        return "No headers found."
    header = "| Level | Header                          | Line |\n|-------|----------------------------------|------|"
    rows = []
    for item in outline_items:
        rows.append(f"| {item['level']:<5} | {item['title']:<32} | {item['line']:<4} |")
    return header + "\n" + "\n".join(rows)
