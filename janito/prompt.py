from .workspace import workset

SYSTEM_PROMPT = """I am Janito, your friendly software development buddy.
I help you with coding tasks while being clear and concise in my responses.
"""

from typing import Optional, List
from pathlib import Path

def inject_workspace_content(files_to_include: Optional[List[Path]] = None) -> str:
    """Build the workspace content string for the prompt.

    Args:
        files_to_include: Optional list of specific files to include in the content.
                         If None, all files in the workset will be included.

    Returns:
        str: The formatted workspace content
    """
    content = ""
    for file in workset._content.files:
        # Skip files not in files_to_include if specified
        if files_to_include is not None:
            if Path(file.name) not in files_to_include:
                continue
        content += f'<file name="{file.name}"\n"'
        content += f'<content>\n"{file.content}"\n</content>\n</file>\n'
    return content

def build_system_prompt(files_to_include: Optional[List[Path]] = None) -> dict:
    """Build the system prompt for the AI agent.

    Args:
        files_to_include: Optional list of specific files to include in the prompt.
                         If None, all files in the workset will be included.

    Returns:
        dict: The system prompt configuration
    """
    system_prompt = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
        }
    ]

    # Get workspace content
    content = inject_workspace_content(files_to_include)
    if content:
        system_prompt.append({
            "type": "text",
            "text": content
        })
    return system_prompt
