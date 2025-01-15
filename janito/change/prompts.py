"""Prompts module for change operations."""

CHANGE_REQUEST_PROMPT = """

Considerng the above workset content, the developer has provided the following request:
{request}

The developer has selected the following action plan:
{action_plan}

Please provide implementation instructions in two formats:

1. Describe the changes in relation to the workset files in the format described below (between CHANGES_START_HERE and CHANGES_END_HERE)
2. The context of workset is always described with lines prefixed with a dot (.) followed by the verbatim content of the line

Examples of line formatting:
# Original line -> How to format in changes
def function():     # -> .def function():
    return False    # -> .    return False
                   # -> .  # empty line needs dot too
# Special case: when original line starts with a dot, add another dot
.import sys         # -> ..import sys
.class MyClass:    # -> ..class MyClass:

3. Use statements and sub-statements to describe changes, for example:

Modify File # this is a statement
name: path/to/file.py
- Replace # this is a sub-statement (starts with dash)
    old_lines:  # mandatory for Replace
    .def old_function():
    .    return False
    new_lines:  # mandatory for Replace
    .def new_function():
    .    print("New implementation")
    .    return True

- Delete  # this is another sub-statement
    old_lines:
    .    print("Debug statement")
    .    print("More debug")
===

# Changes to another file requires a new statement
Modify File   
name: path/to/another/file.py
- Replace
    old_lines:
    .def old_function():
    .    return False
    new_lines:
    .def new_function():
    .    print("New implementation")
    .    return True
===

Important guidelines:
- When modifying Python files:
    * maintain correct indentation
    * when adding imports, place them at the top of the file
    * when adding new types like List, Dict, Tuple, etc, review the imports and add them if missing
- Comments should be included to explain the changes
- Remove code which is obsolete by the change, keep compatibility only when explicitly stated in the request
- Any additional feedback about the changes should be provided after CHANGES_END_HERE
- The old_lines sequence must be present as a continuous block in the original workset file
- When a change is to be applied to non-contiguous lines, use multiple sub-statements, one for each contiguous block

Available statements:
- Create File: Create a new file with specified content
- Delete File: Remove an existing file
- Replace File: Replace entire file content
- Rename File: Change file path/name
- Modify File: Make changes within a file using sub-statements:
    * Replace: Replace old lines with new lines (requires old_lines and new_lines)
    * Delete: Delete sequence of lines (requires old_lines)
    * Add: Add new lines after current_lines or at end of file

CHANGES_START_HERE

# File operations are defined by statements (Create File, Delete File, Replace File, Rename File, Modify File)
# Each statement must be followed by ===

# Create a new file
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

# Delete an existing file
Delete File
name: path/to/delete.py
===

# Replace entire file content
Replace File
name: path/to/replace.py
content:
.# New content for the file
.def new_function():
.    return "Hello World"
===

# Rename a file
Rename File
name: old/path.py
new_name: new/path.py
===

# Modify parts of a file
Modify File
name: path/to/modify.py
# The following sub-statements are supported:
# - Replace: Replace a block of lines with new content
# - Delete: Remove specific lines
# - Add: Insert new lines after specific content or at end of file

# Replace example - old_lines and new_lines are required
- Replace
  old_lines:
  .def old_function():
  .    return False
  new_lines:
  .def new_function():
  .    print("New implementation")
  .    return True

# Delete example - only old_lines required
- Delete
  old_lines:
  .    print("Debug statement")
  .    print("More debug")

# Add example with current_lines - adds after specified lines
- Add
  current_lines:
  .def process_data():
  new_lines:
  .    # Process the input data
  .    # Returns: processed result

# Add example without current_lines - adds at end of file
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
