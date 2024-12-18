"""Shell package initialization for Janito."""
from typing import Optional
from prompt_toolkit import PromptSession
from rich.console import Console
from janito.config import config
from janito.workspace import workspace
from .processor import CommandProcessor
from .commands import register_commands
from .registry import CommandRegistry

def start_shell() -> None:
    """Start the Janito interactive shell."""
    # Create single registry instance
    registry = CommandRegistry()
    
    # Register commands with registry
    register_commands(registry)
    
    # Create shell components with shared registry
    from .prompt import create_shell_session
    session = create_shell_session(registry)
    processor = CommandProcessor(registry)

    # Perform workspace analysis
    console = Console()

    # Use configured paths or default to workspace_dir
    scan_paths = config.include if config.include else [config.workspace_dir]
    workspace.collect_content(scan_paths)
    workspace.analyze()

    # Store workspace content in processor for session
    processor.workspace_content = workspace.get_content()

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