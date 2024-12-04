import re

# Core system prompt focused on role and purpose
SYSTEM_PROMPT = """You are Janito, an AI assistant for software development tasks. Be concise.
"""


CHANGE_ANALISYS_PROMPT = """
Current files:
<files>
{files_content}
</files>

Considering the current files content, provide a table of options for the requested change.
Always provide options using a header label "=== **Option 1** : ...", "=== **Option 2**: ...", etc.
Provide the header with a short description followed by the file changes on the next line
What files should be modified and what should they contain? (one line description)
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

## <uuid4> filename begin "short description of the change" ##
<entire file content>
## <uuid4> filename end ##

ALWAYS provide the entire file content, not just the changes.
If no changes are needed answer to any worksppace just reply <
"""

def build_selected_option_prompt(option_number: int, request: str, initial_response: str, files_content: str = "") -> str:
    """Build prompt for selected option details"""
    options = parse_options(initial_response)
    if option_number not in options:
        raise ValueError(f"Option {option_number} not found in response")
    
    return SELECTED_OPTION_PROMPT.format(
        option_text=options[option_number],
        request=request,
        files_content=files_content
    )

def parse_options(response: str) -> dict[int, str]:
    """Parse options from the response text, including any list items after the option label"""
    options = {}
    pattern = r"===\s*\*\*Option (\d+)\*\*\s*:\s*(.+?)(?====\s*\*\*Option|\Z)"
    matches = re.finditer(pattern, response, re.DOTALL)
    
    for match in matches:
        option_num = int(match.group(1))
        option_text = match.group(2).strip()
        
        # Split into description and list items
        lines = option_text.splitlines()
        description = lines[0]
        list_items = []
        
        # Collect list items that follow
        for line in lines[1:]:
            line = line.strip()
            if line.startswith(('- ', '* ', '• ')):
                list_items.append(line)
            elif not line:
                continue
            else:
                break
                
        # Combine description with list items if any exist
        if list_items:
            option_text = description + '\n' + '\n'.join(list_items)
        
        options[option_num] = option_text
        
    return options


def build_request_analisys_prompt(files_content: str, request: str) -> str:
    """Build prompt for information requests"""

    return CHANGE_ANALISYS_PROMPT.format(
        files_content=files_content,
        request=request
    )
