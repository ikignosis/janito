from pathlib import Path
from typing import List, Dict

def parse_test_file(filepath: Path) -> List[Dict]:
    """Parse a test file containing test cases. Replacement section is optional."""
    test_cases = []
    current_test = {}
    current_section = None
    current_content = []

    try:
        content = filepath.read_text()
        lines = content.splitlines()

        for line in lines:
            if line.startswith("Test: "):
                if current_test:
                    if current_section and current_content:
                        current_test[current_section] = "\n".join(current_content)
                    test_cases.append(current_test)
                current_test = {"name": line[6:].strip(), "expect_success": True}
                current_section = None
                current_content = []
            elif line.startswith("Original:"):
                if current_section and current_content:
                    current_test[current_section] = "\n".join(current_content)
                current_section = "source"
                current_content = []
            elif line.startswith("Search pattern:"):
                if current_section and current_content:
                    current_test[current_section] = "\n".join(current_content)
                current_section = "search"
                current_content = []
            elif line.startswith("Replacement:"):
                if current_section and current_content:
                    current_test[current_section] = "\n".join(current_content)
                current_section = "replacement"
                current_content = []
            elif not line.startswith("="):  # Skip separator lines
                if current_section:
                    current_content.append(line)

        # Add last test case
        if current_test:
            if current_section and current_content:
                current_test[current_section] = "\n".join(current_content)
            test_cases.append(current_test)

        return test_cases
    except Exception as e:
        print(f"Error parsing test file: {e}")
        return []