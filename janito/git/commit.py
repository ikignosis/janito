from pathlib import Path
import subprocess
from typing import Optional
from rich.console import Console
from ..config import config

def git_commit():
    """Perform git commit in the specified directory"""
    console = Console()
    
    try:
        # Check if we're in a git repository
        subprocess.run(['git', 'rev-parse', '--git-dir'], 
                      cwd=config.workdir, 
                      check=True, 
                      capture_output=True)
        
        # Add all changes
        subprocess.run(['git', 'add', '.'], 
                      cwd=config.workdir, 
                      check=True)
        
        # Commit with message
        commit_message = message or "Changes made by Janito"
        subprocess.run(['git', 'commit', '-m', commit_message], 
                      cwd=workdir, 
                      check=True)
        
        console.print("[green]Successfully committed changes to git[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git operation failed: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Error during git commit: {str(e)}[/red]")
