from pathlib import Path
from typing import Optional, Tuple
from rich.console import Console
from rich.panel import Panel

from .parser import parse_response
from .applier.main import ChangeApplier

def play_changes_file(save_file: Path, preview_dir: Path) -> Tuple[bool, Optional[str]]:
    """
    Load and apply changes from a saved file.
    """
    try:
        if not save_file.exists():
            return False, f"Save file not found: {save_file}"
            
        saved_content = save_file.read_text()
        file_type = determine_history_file_type(save_file)
        
        # Handle failed changes debug file
        if file_type == 'changes_failed':
            console = Console()
            console.print("\n[yellow]Debug information for failed search:[/yellow]")
            console.print(Panel(saved_content))
            return True, None
            
        # Extract changes section if it's a history file
        if file_type == 'changes':
            changes_section = saved_content.split("Changes:\n", 1)
            if len(changes_section) > 1:
                saved_content = changes_section[1].strip()
        
        # Parse the changes using the parser module
        changes = parse_response(saved_content)
            
        if not changes:
            return False, "No valid changes found in file"
            
        # Apply changes using ChangeApplier
        applier = ChangeApplier(preview_dir)
        success, modified_files = applier.apply_changes(changes)
        
        if not success:
            return False, "Failed to apply changes"
            
        return True, None
        
    except Exception as e:
        return False, f"Error playing changes: {str(e)}"
