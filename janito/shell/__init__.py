"""Shell package initialization for Janito."""
from typing import Optional
from prompt_toolkit import PromptSession
from rich.console import Console
from janito.config import config
from janito.workspace.workset import Workset
from .processor import CommandProcessor
from .commands import register_commands
from .registry import CommandRegistry

def start_shell() -> None:
    """Start the Janito interactive shell."""
    # Create single registry instance
    registry = CommandRegistry()
    register_commands(registry)
    
    # Create shell components with shared registry
    from .prompt import create_shell_session
    session = create_shell_session(registry)
    processor = CommandProcessor(registry)

    # Initialize workset content
    console = Console()
    workset = Workset()
    workset.refresh()
    workset.analyze()

    # Store workset content in processor for session
    processor.workspace_content = workset.content

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