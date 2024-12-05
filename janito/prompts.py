import re
import uuid  # Add import for uuid

# Core system prompt focused on role and purpose
SYSTEM_PROMPT = """You are Janito, your friendly AI-powered software development buddy. I help you with coding tasks while being clear and concise in my responses."""


CHANGE_ANALISYS_PROMPT = """
Current files:
<files>
{files_content}
</files>

Considering the above current files content, provide options for the requested change in the following format:

FORMAT:
    A. Keyword summary of the change
    -----------------
    Affected files:
    - file1.py, file2.py,  ...

    Description:
    - Detailed description of the change


Do not provide the content of any of the file suggested to be created or modified.

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
    options = parse_options(initial_response)
    if option not in options:
        raise ValueError(f"Option {option} not found in response")
    
    short_uuid = str(uuid.uuid4())[:8]  # Generate a short UUID
    
    return SELECTED_OPTION_PROMPT.format(
        option_text=options[option],
        request=request,
        files_content=files_content,
        uuid=short_uuid  # Pass the short UUID
    )

def parse_options(response: str) -> dict[str, str]:
    """Parse options from the response text using letter-based format"""
    options = {}
    pattern = r'([A-Z])\.\s+([^\n]+)\s+-+\s+(.*?)(?=[A-Z]\.|$)'
    matches = re.finditer(pattern, response, re.DOTALL)
    
    for match in matches:
        option_letter = match.group(1)
        summary = match.group(2).strip()
        details = match.group(3).strip()
        
        # Combine summary with details
        option_text = f"{summary}\n{details}"
        options[option_letter] = option_text
        
    return options

def build_request_analisys_prompt(files_content: str, request: str) -> str:
    """Build prompt for information requests"""

    return CHANGE_ANALISYS_PROMPT.format(
        files_content=files_content,
        request=request
    )