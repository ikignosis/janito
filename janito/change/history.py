from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from janito.config import config

# Set fixed timestamp when module is loaded
APP_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

def get_history_path() -> Path:
    """Create and return the history directory path"""
    history_dir = config.workspace_dir / '.janito' / 'change_history'
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
    history_file.write_text(history_content, encoding='utf-8')
    return history_file

def get_latest_changes_file() -> Optional[Path]:
    """Find and return the path to the most recent changes file in history.
    
    Returns:
        Path to the most recent changes file, or None if no changes files exist
    """
    history_dir = get_history_path()
    changes_files = [f for f in history_dir.glob("*_changes.txt")]
    
    if not changes_files:
        return None
        
    # Sort by modification time, newest first
    return max(changes_files, key=lambda p: p.stat().st_mtime)