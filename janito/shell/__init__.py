"""Shell package initialization for Janito."""
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path
from rich.console import Console
from janito.config import config
from janito.scan import collect_files_content
from janito.scan.analysis import analyze_workspace_content
from .processor import CommandProcessor

def start_shell() -> None:
    """Start the Janito interactive shell."""
    history_file = Path.home() / ".janito_history"
    session = PromptSession(history=FileHistory(str(history_file)))
    processor = CommandProcessor()

    # Perform workspace analysis
    console = Console()

    # Use configured paths or default to workdir
    scan_paths = config.include if config.include else [config.workdir]
    content = collect_files_content(scan_paths)
    analyze_workspace_content(content)

    # Store analysis results in processor for session
    processor.workspace_content = content

    while True:
        try:
            text = session.prompt("janito🤖 ")
            if text.strip():
                processor.process_command(text)
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")
    print("Goodbye!")