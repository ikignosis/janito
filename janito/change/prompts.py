"""Prompts module for change operations."""

CHANGE_REQUEST_PROMPT = """

Considerng the above workset content, the developer has provided the following request:
{request}

The developer has selected the following action plan:
{action_plan}

Please provide implementation instructions in two formats:

1. Describe the changes in relation to the workset files in the format described below (between CHANGES_START_HERE and CHANGES_END_HERE)
1.1 be concise identifying the files and the changes to be made


Rules:
- Each statement must be separated with "===", sub-statements are prefixed with "-"
- For Create File: content must be prefixed with dots (.)
- For Modify File:
  * All multiline content must be prefixed with dots (.)
  * new_indent: number of spaces for indentation (only required if the indent is different from the original indent)
  * Empty lines in content should also be prefixed with a dot (.)
  * Consolidate all changes into a single Modify File statement with multiple substatements
- When adding imports, place them at the top of the file
- When modifying Python files, maintain correct indentation
- Comments should be included to explain the changes
- Any additional feedback about the changes should be provided after CHANGES_END_HERE

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

# Modify File
Modify File
name: path/to/modify.py

# The Modify File supports these selection operations:
# - Select Over: Select lines between and including start and end lines
# - Select Exact: Select lines from source matching exact lines: content

# Each selection can be followed by:
# - Delete: Remove selected lines
# - Replace: Replace selected lines with new content
# - Insert: Insert new content before selected lines
# - Append: Append new content after selected lines

# Example: Replace a function implementation
- Select Over
    start_lines:
    .def old_function():
    end_lines:
    .    return False
- Replace
    new_content:
    .def new_function():
    .    print("New implementation")
    .    return True
    new_indent: 4

# Example: Delete specific lines
- Select Exact
    lines:
    .    print("Debug statement")
- Delete

# Example: Insert comments before a function
- Select Exact
    lines:
    .def process_data():
- Insert
    new_content:
    .# Process the input data
    .# Returns: processed result

# Example: Append comments after a block
- Select Over
    start_lines:
    .def validate():
    end_lines:
    .    return True
- Append
    new_content:
    .# End of validation function
    .# Consider adding more checks

===

CHANGES_END_HERE

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
