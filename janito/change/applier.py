from pathlib import Path
from typing import Tuple, Optional
from rich.console import Console
from rich import box
from rich.panel import Panel

from janito.fileparser import FileChange
from janito.config import config
from .position import find_text_positions, format_whitespace_debug
from .indentation import adjust_indentation

def apply_single_change(filepath: Path, change: FileChange, workdir: Path, preview_dir: Path) -> Tuple[bool, Optional[str]]:
    """Apply a single file change"""
    preview_path = preview_dir / filepath
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    
    if change.remove_file:
        orig_path = workdir / filepath
        if not orig_path.exists():
            return False, f"Cannot remove non-existent file {filepath}"
        if config.debug:
            console = Console()
            console.print(f"\n[red]Removing file {filepath}[/red]")
        # For preview, we don't create the file in preview dir
        return True, None
    
    if config.debug:
        console = Console()
        console.print(f"\n[cyan]Processing change for {filepath}[/cyan]")
        console.print(f"[dim]Change type: {'new file' if change.is_new_file else 'modification'}[/dim]")
    
    if change.is_new_file or change.replace_file:
        if change.is_new_file and filepath.exists():
            return False, "Cannot create file - already exists"
        if config.debug:
            action = "Creating new" if change.is_new_file else "Replacing"
            console.print(f"[cyan]{action} file with content:[/cyan]")
            console.print(Panel(change.content, title="File Content"))
        preview_path.write_text(change.content)
        return True, None
        
    orig_path = workdir / filepath
    if not orig_path.exists():
        return False, f"Cannot modify non-existent file {filepath}"
        
    content = orig_path.read_text()
    modified = content
    
    for search, replace, description in change.search_blocks:
        if config.debug:
            console.print(f"\n[cyan]Processing search block:[/cyan] {description or 'no description'}")
            console.print("[yellow]Search text:[/yellow]")
            console.print(Panel(format_whitespace_debug(search)))
            if replace is not None:
                console.print("[yellow]Replace with:[/yellow]")
                console.print(Panel(format_whitespace_debug(replace)))
            else:
                console.print("[yellow]Action:[/yellow] Delete text")
                
        positions = find_text_positions(modified, search)
        
        if config.debug:
            console.print(f"[cyan]Found {len(positions)} matches[/cyan]")
        
        if not positions:
            error_context = f" ({description})" if description else ""
            debug_search = format_whitespace_debug(search)
            debug_content = format_whitespace_debug(modified)
            error_msg = (
                f"Could not find search text in {filepath}{error_context}:\n\n"
                f"[yellow]Search text (with whitespace markers):[/yellow]\n"
                f"{debug_search}\n\n"
                f"[yellow]File content (with whitespace markers):[/yellow]\n"
                f"{debug_content}"
            )
            return False, error_msg
            
        # Apply replacements from end to start to maintain position validity
        for start, end in reversed(positions):
            if config.debug:
                console.print(f"\n[cyan]Replacing text at positions {start}-{end}:[/cyan]")
                console.print("[yellow]Original segment:[/yellow]")
                console.print(Panel(format_whitespace_debug(modified[start:end])))
                if replace is not None:
                    console.print("[yellow]Replacing with:[/yellow]")
                    console.print(Panel(format_whitespace_debug(replace)))
            
            # Adjust replacement text indentation
            original_segment = modified[start:end]
            adjusted_replace = adjust_indentation(original_segment, replace) if replace else ""
            
            if config.debug and replace:
                console.print("[yellow]Adjusted replacement:[/yellow]")
                console.print(Panel(format_whitespace_debug(adjusted_replace)))
                    
            modified = modified[:start] + adjusted_replace + modified[end:]
    
    if modified == content:
        if config.debug:
            console.print("\n[yellow]No changes were applied to the file[/yellow]")
        return False, "No changes were applied"
        
    if config.debug:
        console.print("\n[green]Changes applied successfully[/green]")
        
    preview_path.write_text(modified)
    return True, None