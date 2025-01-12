"""
This package provides the following change flow steps:

- Create a preview directory
- Build change request prompt
- Send change request to AI agent
- Parse the response into changes
- Save response to history file
- Preview the changes (applying them to the preview directory)
- Validate the changes
- Run tests if specified
- Show the change view (using janito.changeviewer)
- Prompt the user to apply the changes to the working directory
- Apply the changes
"""

from typing import Tuple
from pathlib import Path
from ..agents import agent  # Updated import to use singleton directly
from .preview import setup_workspace_dir_preview
from .applier.main import ChangeApplier

__all__ = [
    'build_change_request_prompt',
    'get_change_response',
    'parse_response',
    'setup_workspace_dir_preview',
    'parse_change_response',
    'save_change_response',
    'ChangeApplier'
]
