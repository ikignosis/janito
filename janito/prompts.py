import re
import uuid
from typing import List, Union
from dataclasses import dataclass
from .analysis import parse_analysis_options, AnalysisOption

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

RULES:
- When removing constants, ensure they are not used elsewhere
- When adding new features to python files, add the necessary imports
- Python imports should be inserted at the top of the file
- For complete file replacements, only use for existing files marked as modified
- File replacements must preserve the essential functionality
- When multiple changes affect the same code block, combine them into a single change
- if no changes are required answer only the reason in the format: <no_changes_required>reason for no changes<no_changes_required>

Please provide the changes in this format:

For incremental changes:
## {uuid} file <filepath> modify "short file change description" ##
## {uuid} search/replace "short change description" ##
<search_content>
## {uuid} replace with ##
<replace_content>
## {uuid} file end ##

For complete file replacement (only for existing modified files):
## {uuid} file <filepath> replace "short file description" ##
<full_file_content>
## {uuid} file end ##

For new files:
## {uuid} file <filepath> create "short file description" ##
<full_file_content>
## {uuid} file end ##

For content deletion:
## {uuid} file <filepath> modify ##
## {uuid} search/delete "short change description" ##
<content_to_delete>
## {uuid} file end ##

For file removal:
## {uuid} file <filepath> remove "short removal reason" ##
## {uuid} file end ##

RULES:
1. search_content MUST preserve the original indentation/whitespace
2. file replacement can only be used for existing files marked as 
"""

def build_selected_option_prompt(option_text: str, request: str, files_content: str = "") -> str:
    """Build prompt for selected option details
    
    Args:
        option_text: Formatted text describing the selected option
        request: The original user request
        files_content: Content of relevant files
    """
    short_uuid = str(uuid.uuid4())[:8]
    
    return SELECTED_OPTION_PROMPT.format(
        option_text=option_text,
        request=request,
        files_content=files_content,
        uuid=short_uuid
    )
