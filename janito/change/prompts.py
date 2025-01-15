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
- Use statements and sub-statements to describe changes
e.g:
    Modify File # this is a statement
    - Replace # this is a sub-statement (starts with dash)
    ###
- Use "===" to separate statements, sub-statements beloging to the same statement must NOT be separated
- All content old and new lines must be prefixed with an extra dot (.) regardless of the language
   * Empty lines in content should also be prefixed with an extra dot (.)
   * Lines whose content had already a leading dot (.) must be prefixed with an extra dot (.)
- When adding imports, place them at the top of the file
- When modifying Python files, maintain correct indentation
- When adding imports, place them at the top of the file
- When modifying Python files, maintain correct indentation
- Comments should be included to explain the changes
- Remove code which is obsolete by the change, keep compatibility only when explicited stated in the request
- Any additional feedback about the changes should be provided after CHANGES_END_HERE

The following are the multiple support sub-statements for the Modify File statement:

- Replace: Replace old lines with new lines
- Delete: Delete sequence of lines matching old_lines
- Add: Add new lines after current_lines (or at end of file if current_lines not specified)

Note: The old_lines sequence must be present as a continuous block in the original workset file, 
when a change is to be applied to non contiguous lines, you need to use multiple sub-statements. one for each contiguous block.

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

# Example of a Replace File statement
Replace File
name: path/to/replace.py
content:
.# New content for the file
.def new_function():
.    return "Hello World"
===

# Example of a Rename File
Rename File
name: old/path.py
new_name: new/path.py
===

# Modify File
Modify File
name: path/to/modify.py

# The Modify File supports these operations:
# - Replace: Replace old lines with new lines
# - Delete: Delete sequence of lines matching old_lines
# - Add: Add new lines after current_lines (or at end of file if current_lines not specified)

# Modify File Examples:

# Example: Replace lines
- Replace
  old_lines:
  .def old_function():
  .    return False
  new_lines:
  .def new_function():
  .    print("New implementation")
  .    return True

# Example: Delete lines
- Delete
  old_lines:
  .    print("Debug statement")
  .    print("More debug")

# Example: Add lines after specific content
- Add
  current_lines:
  .def process_data():
  new_lines:
  .    # Process the input data
  .    # Returns: processed result

# Example: Add lines at end of file
- Add
  new_lines:
  .# End of file comment
  .# Consider adding more functionality

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
