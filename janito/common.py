from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from janito.claude import ClaudeAPIAgent

def progress_send_message(claude: ClaudeAPIAgent, message: str) -> str:
    """
    Send a message to Claude with a progress indicator and elapsed time.
    
    Args:
        claude: The Claude API agent instance
        message: The message to send
        
    Returns:
        The response from Claude
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Waiting for response from Claude...", total=None)
        response = claude.send_message(message)
        progress.update(task, completed=True)
    return response