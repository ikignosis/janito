from pathlib import Path
from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from janito.agents import AgentSingleton
from janito.prompts import SYSTEM_PROMPT
from .display import create_completer, format_prompt, display_welcome
from .commands import process_command

def start_console_session(workdir: Path, include: Optional[List[Path]] = None) -> None:
    """Start an enhanced interactive console session"""
    console = Console()
    agent = AgentSingleton.get_agent()

    # Setup history with persistence
    history_file = workdir / '.janito' / 'console_history'
    history_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create session with history and completions
    session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=create_completer(workdir),
        auto_suggest=AutoSuggestFromHistory(),
        complete_while_typing=True
    )

    display_welcome(workdir)

    while True:
        try:
            # Get input with formatted prompt
            user_input = session.prompt(
                lambda: format_prompt(workdir),
                complete_while_typing=True
            ).strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ('exit', 'quit'):
                console.print("\n[cyan]Goodbye! Have a great day![/cyan]\n")
                break

            # Split input into command and args
            parts = user_input.split(maxsplit=1)
            if parts[0].startswith('/'):  # Handle /command format
                command = parts[0][1:]  # Remove the / prefix
            else:
                command = "request"  # Default to request if no command specified
                
            args = parts[1] if len(parts) > 1 else ""
            
            # Process command with separated args
            process_command(command, args, workdir, include, claude)

        except KeyboardInterrupt:
            continue
        except EOFError:
            console.print("\n[cyan]Goodbye! Have a great day![/cyan]\n")
            break
