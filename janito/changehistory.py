from pathlib import Path
from datetime import datetime
from typing import Optional

# Set fixed timestamp when module is loaded
APP_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def get_history_path(workdir: Path) -> Path:
    """Create and return the history directory path"""
    history_dir = workdir / '.janito' / 'change_history'
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def determine_history_file_type(filepath: Path) -> str:
    """Determine the type of saved file based on its name"""
    name = filepath.name.lower()
    if 'changes' in name:
        return 'changes'
    elif 'selected' in name:
        return 'selected'
    elif 'analysis' in name:
        return 'analysis'
    elif 'response' in name:
        return 'response'
    return 'unknown'

def save_changes_to_history(content: str, request: str, workdir: Path) -> Path:
    """Save change content to history folder with timestamp and request info"""
    history_dir = get_history_path(workdir)
    
    # Create history entry with request and changes
    history_file = history_dir / f"changes_{APP_TIMESTAMP}.txt"
    
    history_content = f"""Request: {request}
Timestamp: {APP_TIMESTAMP}

Changes:
{content}
"""
    history_file.write_text(history_content)
    return history_file

def get_history_file_path(workdir: Path) -> Path:
    """Get path for a history file with app timestamp"""
    history_path = get_history_path(workdir)
    return history_path / f"{APP_TIMESTAMP}_changes.txt"