import re
import uuid
from typing import List
from dataclasses import dataclass
from .analysis import parse_analysis_options

# Core system prompt focused on role and purpose
SYSTEM_PROMPT = """I am Janito, your friendly software development buddy. I help you with coding tasks while being clear and concise in my responses."""


SELECTED_OPTION_PROMPT = """
Original request: {request}

Please provide detailed implementation using the following guide:
{option_text}

Current files:
<files>
{files_content}
</files>

After checking the above files and the provided implementation, please provide the changes per the following format:

## {uuid} file <filepath> modify "short description of the changes" ##
## {uuid} change begin ##
<change_content>
## {uuid} change end ##
## {uuid} file end ##

RULES:
- Prefix every line in change_context with one of:
  "=" for context lines to match location
  ">" for lines to be added
  "<" for lines to be deleted
- Provide enough context lines before and after the change to locate the original content
- Preserve empty lines exactly as they appear in the file
- Empty lines should be prefixed with "=" for context or ">" for additions

For file creations use:

## {uuid} file <filepath> create "short description of the new file" ##
<full_file_content>
## {uuid} file end ##
full_file_content should contain the entire content of the new file without any prefixes.
Preserve all empty lines exactly as they should appear in the file.

"""

def build_selected_option_prompt(option: str, request: str, initial_response: str, files_content: str = "") -> str:
    """Build prompt for selected option details"""
    options = parse_analysis_options(initial_response)  # Update function call
    
    short_uuid = str(uuid.uuid4())[:8]  # Generate a short UUID
    
    return SELECTED_OPTION_PROMPT.format(
        option_text=options[option],
        request=request,
        files_content=files_content,
        uuid=short_uuid  # Pass the short UUID
    )
