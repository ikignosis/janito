from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from janito.agents import agent
from .config import config

console = Console()

def progress_send_message(message: str) -> str:
    """
    Send a message to the AI agent with a progress indicator and elapsed time.
    
    Args:
        message: The message to send
        
    Returns:
        The response from the AI agent
    """
    if config.debug:
        console.print("[yellow]======= Sending message[/yellow]")
        print(message)
        console.print("[yellow]======= End of message[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}", justify="center"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Waiting for response from AI agent...", total=None)
        response = agent.send_message(message)
        progress.update(task, completed=True)

    if config.debug:
        console.print("[yellow]======= Received response[/yellow]")
        print(response)
        console.print("[yellow]======= End of response[/yellow]")
    return response