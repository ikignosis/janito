"""Prompts module for change operations."""

CHANGE_REQUEST_PROMPT = """
Original request: {request}

Please provide implementation instructions using the following format:

CHANGES_START_HERE

# File operations should be in this format:
Create File
name: path/to/file.py
content:
.from typing import Optional
.
.def process_data(value: str) -> Optional[str]:
.    if not value:
.        return None
.    return value.upper()

Delete File
name: path/to/delete.py

Rename File
source: old/path.py
target: new/path.py

# Modify operations use substatements for changes:
Modify File
name: path/to/modify.py
- Replace  # Example 1: Replace entire function with validation
    start_context:
    .def validate(data: str):
    .    return data.strip() != ""
    end_context:
    new_content:
    .def validate(data: str) -> bool:
    .    if not isinstance(data, str):
    .        raise TypeError("data must be a string")
    .    return data.strip() != ""
    preserve_context: false

- Replace  # Example 2: Replace function body while preserving definition
    start_context:
    .def process_item(self, item: dict) -> dict:
    .    # Basic processing
    .    return {"id": item["id"], "value": item["value"]}
    end_context:
    new_content:
    .    # Enhanced processing with validation
    .    if not isinstance(item, dict):
    .        raise TypeError("item must be a dictionary")
    .    return {
    .        "id": item["id"],
    .        "value": item["value"],
    .        "processed": True
    .    }
    preserve_context: true
    indent: 4

- Replace  # Example 3: Replace nested method with proper indentation
    start_context:
    .    def nested_method(self):
    .        pass
    end_context:
    new_content:
    .        # Properly indented nested method
    .        result = self.process()
    .        if result:
    .            return result.value
    .        return None
    preserve_context: true
    indent: 8  # Indented for class method

END_OF_CHANGES

Rules:
- Each operation must be separated by a blank line
- For Create File: content must be prefixed with dots (.)
- For Modify File:
  * Uses substatements starting with "- Replace"
  * Each substatement has its own context and content fields
  * All multiline content must be prefixed with dots (.)
  * preserve_context: true - keeps the function definition, replaces only the body
  * preserve_context: false - replaces the entire block including the definition
  * indent: number of spaces to indent new content (e.g., 4 for functions, 8 for class methods)
  * Empty lines in content should also be prefixed with a dot (.)
- When adding imports, place them at the top of the file
- When modifying Python files, maintain correct indentation
- Comments should be included to explain the changes
- Any additional feedback about the changes should be provided after END_OF_CHANGES

{option_text}
"""