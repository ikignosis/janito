"""Prompts module for change operations."""

CHANGE_REQUEST_PROMPT = """

Considerng the above workset content, the developer has provided the following request:
{request}

The developer has selected the following action plan:
{action_plan}

Please provide implementation instructions in two formats:

1. Changes described in your own format (between OWN_FORMAT_START and OWN_FORMAT_END)
1.1 be concise identifying the files and the changes to be made
1.2 be specific to the workset content

2. Describe the changes in relation to the workset content in the format described below (between CHANGES_START_HERE and CHANGES_END_HERE)
2.1 be concise identifying the files and the changes to be made
2.2 be specific to the workset content

Rules:
- Each statement must be separated with "===", sub-statements are prefixed with "-"
- For Create File: content must be prefixed with dots (.)
- For Modify File Content:
  * Delete Block: removes the block and its before/after lines
  * All multiline content must be prefixed with dots (.)
  * new_indent: number of spaces for indentation (only required if the indent is different from the original indent)
  * Empty lines in content should also be prefixed with a dot (.)
  * Consolidate all changes into a single Modify File Content statement with multiple Replace Block and Delete Block substatements
- When adding imports, place them at the top of the file
- When modifying Python files, maintain correct indentation
- Comments should be included to explain the changes
- Any additional feedback about the changes should be provided after END_OF_CHANGES


CHANGES_START_HERE

# Example of a Create File statement
Create File
name: path/to/file.py
content:
.from typing import Optional
.
.def process_data(value: str) -> Optional[str]:
.    if not value:
.        return None
.    return value.upper()
===

# Example of a Delete File statement
Delete File
name: path/to/delete.py
===

# Example of a Rename File statement
name: old/path.py
new_name: new/path.py
===

# Modify file content
Modify File Content
name: path/to/modify.py


# The modify file content supports the substatements: Replace Block and Delete Block

- Replace Block # Replace entire block including before and after lines
    before_lines:
    .def validate(data: str) -> bool:
    .    result = data.strip() != ""
    # ... existing content ...
    after_lines:
    .    return result
    new_content:
    # Replace before_lines + <existing content> + after_lines -> <new content>
    .def validate(data: int):
    .    result = data > 0
    .    return result
    # new_indent: 4 # number of spaces for indentation (only required if the indent is different from the original indent)

NOTE: the before_lines and after_lines are removed from the original content, if you want to keep them, add them in the new_content !

- Delete Block  # Delete block including before and after lines
    before_lines:
    .    # Deprecated code start
    after_lines:
    .    # Deprecated code end
===

END_OF_CHANGES

"""

from pathlib import Path
from typing import Optional, List
from janito.workspace import workset
from janito.config import config
from janito.common import progress_send_message

def build_change_request_prompt(request: str, action_plan: str) -> str:
    """Build a prompt for the change request that includes workspace metadata.

    Args:
        request: The original change request from the user

    Returns:
        str: A complete prompt including the request and workspace metadata
    """
    return CHANGE_REQUEST_PROMPT.format(
        request=request,
        action_plan=action_plan
    )
