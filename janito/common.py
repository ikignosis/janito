from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.console import Console
from rich.rule import Rule
from janito.agents import agent
from .config import config
from rich import print

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
    response_text = response.content[0].text
    
    # Add token usage summary with detailed cache info
    usage = response.usage
    
    # Format cache info
    cache_str = "(no cache used)"
    if usage.cache_creation_input_tokens or usage.cache_read_input_tokens:
        create_pct = (usage.cache_creation_input_tokens / usage.input_tokens) * 100
        read_pct = (usage.cache_read_input_tokens / usage.input_tokens) * 100
        cache_str = f"(cached in/out: {usage.cache_creation_input_tokens}[{create_pct:.1f}%]/{usage.cache_read_input_tokens}[{read_pct:.1f}%])"
    
    percentage = (usage.output_tokens / usage.input_tokens) * 100
    usage_text = f"Tokens: {usage.input_tokens} sent {cache_str}, {usage.output_tokens} received ({percentage:.1f}% ratio)"
    console.print(Rule(usage_text, style="blue", align="center"))
    
    return response_text