import re
from typing import List, Dict


def parse_java_outline(lines: List[str]) -> List[Dict]:
    """
    Parses Java source code lines and extracts classes and methods with their signatures.
    Returns a list of outline items: {type, name, return_type, parameters, generics, line}
    """
    outline = []
    class_pattern = re.compile(r"\bclass\s+(\w+)(\s*<[^>]+>)?")
    # Match methods with or without visibility modifiers (including package-private)
    method_pattern = re.compile(
        r"^(?:\s*(public|protected|private)\s+)?(?:static\s+)?([\w<>\[\]]+)\s+(\w+)\s*\(([^)]*)\)"
    )
    current_class = None
    for idx, line in enumerate(lines, 1):
        class_match = class_pattern.search(line)
        if class_match:
            class_name = class_match.group(1)
            generics = class_match.group(2) or ""
            outline.append(
                {
                    "type": "class",
                    "name": class_name,
                    "generics": generics.strip("<>") if generics else None,
                    "line": idx,
                }
            )
            current_class = class_name
        else:
            method_match = method_pattern.search(line)
            if method_match:
                return_type = method_match.group(2)
                method_name = method_match.group(3)
                params = method_match.group(4)
                outline.append(
                    {
                        "type": "method",
                        "class": current_class,
                        "name": method_name,
                        "return_type": return_type,
                        "parameters": params.strip(),
                        "line": idx,
                    }
                )
    return outline
