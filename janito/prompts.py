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

Please provide the changes in this format:

## {uuid} file <filepath> modify "short description" ##
## {uuid} search/replace ##
<search_content>
## {uuid} replace with ##
<replace_content>
## {uuid} file end ##

Or to delete content:
## {uuid} file <filepath> modify "short description" ##
## {uuid} search/delete ##
<content_to_delete>
## {uuid} file end ##

For new files:
## {uuid} file <filepath> create "short description" ##
<full_file_content>
## {uuid} file end ##
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
