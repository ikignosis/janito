import re
import uuid
from typing import List
from dataclasses import dataclass

# Core system prompt focused on role and purpose
SYSTEM_PROMPT = """I am Janito, your friendly software development buddy. I help you with coding tasks while being clear and concise in my responses."""

@dataclass
class AnalysisOption:
    letter: str
    summary: str
    affected_files: List[str]
    description: str  # Changed from description_items to single description

CHANGE_ANALISYS_PROMPT = """
Current files:
<files>
{files_content}
</files>

Considering the above current files content, provide options for the requested change in the following format:

A. Keyword summary of the change
-----------------
Description:
A clear and concise description of the proposed changes and their impact.

Affected files:
- file1.py
- file2.py (new)


RULES:
- options are split by an empty line
- do NOT provide the content of the files



Request:
{request}
"""

SELECTED_OPTION_PROMPT = """
Original request: {request}

Please provide detailed implementation using the following guide:
{option_text}

Current files:
<files>
{files_content}
</files>

After checking the above files and the provided implementation, please provide the following:

## {uuid} filename begin "short description of the change" ##
<entire file content>
## {uuid} filename end ##

ALWAYS provide the entire file content, not just the changes.
If no changes are needed answer to any worksppace just reply <
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

def parse_analysis_options(response: str) -> dict[str, AnalysisOption]:
    """Parse options from the response text using letter-based format"""
    options = {}
    pattern = r'([A-Z])\.\s+([^\n]+)\s+-+\s+(.*?)(?=[A-Z]\.|$)'
    matches = re.finditer(pattern, response, re.DOTALL)
    
    for match in matches:
        option_letter = match.group(1)
        summary = match.group(2).strip()
        details = match.group(3).strip()
        
        files = []
        description = ""
        
        # Split into sections
        sections = details.split('Description:')
        if len(sections) > 1:
            desc_section = sections[1].split('Affected files:')[0]
            description = desc_section.strip()  # Keep as single text
            
            # Parse affected files if present
            if 'Affected files:' in sections[1]:
                files_section = sections[1].split('Affected files:')[1]
                files = [f.strip(' -\n') for f in files_section.strip().split('\n') if f.strip()]
        
        option = AnalysisOption(
            letter=option_letter,
            summary=summary,
            affected_files=files,
            description=description
        )
        options[option_letter] = option
        
    return options

def build_request_analisys_prompt(files_content: str, request: str) -> str:
    """Build prompt for information requests"""

    return CHANGE_ANALISYS_PROMPT.format(
        files_content=files_content,
        request=request
    )