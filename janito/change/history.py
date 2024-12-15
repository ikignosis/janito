from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from janito.config import config
from janito.change.parser import parse_response
from janito.change.applier import ChangeApplier

# Set fixed timestamp when module is loaded
APP_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def get_history_path() -> Path:
    """Create and return the history directory path"""
    history_dir = config.workdir / '.janito' / 'change_history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def determine_history_file_type(filepath: Path) -> str:
    """Determine the type of saved file based on its name"""
    name = filepath.name.lower()
    if '_changes_failed' in name:
        return 'changes_failed'
    elif 'changes' in name:
        return 'changes'
    elif 'selected' in name:
        return 'selected'
    elif 'analysis' in name:
        return 'analysis'
    elif 'response' in name:
        return 'response'
    return 'unknown'

def save_changes_to_history(content: str, request: str) -> Path:
    """Save change content to history folder with timestamp and request info"""
    history_dir = get_history_path()
    
    # Create history entry with request and changes
    filename = f"{APP_TIMESTAMP}_changes.txt"
    history_file = history_dir / filename
    history_content = f"""Request: {request}
Timestamp: {APP_TIMESTAMP}

Changes:
{content}
"""
    history_file.write_text(history_content)
    return history_file


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