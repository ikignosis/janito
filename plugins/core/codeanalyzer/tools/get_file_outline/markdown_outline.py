import re
from typing import List


def parse_markdown_outline(lines: List[str]):
    header_pat = re.compile(r"^(#+)\s+(.*)")
    outline = []
    for idx, line in enumerate(lines):
        match = header_pat.match(line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            outline.append({"level": level, "title": title, "line": idx + 1})
    return outline
