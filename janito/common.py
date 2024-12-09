from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from janito.agents import AgentSingleton

def progress_send_message(message: str) -> str:
    """
    Send a message to the AI agent with a progress indicator and elapsed time.
    
    Args:
        message: The message to send
        
    Returns:
        The response from the AI agent
    """
    agent = AgentSingleton.get_agent()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}", justify="center"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Waiting for response from AI agent...", total=None)
        response = agent.send_message(message)
        progress.update(task, completed=True)
    return response