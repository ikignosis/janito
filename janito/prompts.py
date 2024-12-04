import re

# Core system prompt focused on role and purpose
SYSTEM_PROMPT = """You are Janito, an AI assistant for software development tasks. Be concise.
"""

EMPTY_DIR_PROMPT = """
This is an empty directory. What files should be created and what should they contain? (one line description)
Allways provide options using a  header label "=== **Option 1** : ...", "=== **Option 2**: ...", etc.

Request:
{request}
"""

NON_EMPTY_DIR_PROMPT = """
Current files:
<files>
{files_content}
</files>

Always provide options using a header label "=== **Option 1** : ...", "=== **Option 2**: ...", etc.
Provide the header with a short description followed by the file changes on the next line
What files should be modified and what should they contain? (one line description)
Do not provide the content of any of the file suggested to be created or modified.

Request:
{request}
"""

SELECTED_OPTION_PROMPT = """
Original request: {request}

Please provide detailed implementation using the following instructions as a guide:
{option_text}

Current files:
<files>
{files_content}
</files>

Original request: {request}

Please provide implementation details following these guidelines:
- Provide only the changes, no additional information
- The changes must be described as a series of find/replace/delete or create_file operations

- Use the following format for each change:
    ## <uuid> filename:operation ##
    ## <uuid> find_content ##
    <oldContent> must be a unique part in the original file
    ## <uuid> replace_content  ##
    <newContent> will fully replace the oldContent
    ## <uuid> delete_content  ##
    <oldContent> will be removed from the file
    ## <uuid> end  ##

The supported operations are: 
    - find_replace, which will find oldContent and replace it newContent
    - create_file, which creates a new file with newContent

Rules:
    - Use the same <uuid> for all the blocks
    - For missing files, respond with: <error>reason</error>

Notes:
    - Content blocks must match exactly
    - Indentation and whitespace are significant
    - File paths must be relative to the root
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
    if not files_content.strip():
        return EMPTY_DIR_PROMPT.format(request=request)
    return NON_EMPTY_DIR_PROMPT.format(
        files_content=files_content,
        request=request
    )
