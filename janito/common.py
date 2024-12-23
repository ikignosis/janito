from datetime import datetime, timezone
from rich.live import Live
from rich.text import Text
from rich.console import Console
from rich.rule import Rule
from rich import print
from threading import Event, Thread
from time import sleep
from janito.agents import agent
from .config import config

""" CACHE USAGE SUMMARY
https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
cache_creation_input_tokens: Number of tokens written to the cache when creating a new entry.
cache_read_input_tokens: Number of tokens retrieved from the cache for this request.
input_tokens: Number of input tokens which were not read from or used to create a cache.
"""

from janito.prompt import build_system_prompt

console = Console()

def progress_send_message(message: str) -> str:
    """Send a message to the AI agent with progress indication.

    Displays a progress spinner while waiting for the agent's response and shows
    token usage statistics after receiving the response. Uses a background thread
    to update the elapsed time display.
    
    Displays a progress spinner while waiting for the agent's response and shows
    token usage statistics after receiving the response.
    
    Args:
        message: The message to send to the AI agent
        
    Returns:
        str: The response text from the AI agent
        
    Note:
        If the request fails or is canceled, returns the error message as a string
    """
    system_message = build_system_prompt()
    if config.debug:
        console.print("[yellow]======= Sending message[/yellow]")
        print(system_message)
        print(message)
        console.print("[yellow]======= End of message[/yellow]")

    start_time = datetime.now()
    stop_event = Event()

    def update_display_thread(live_display):
        while not stop_event.is_set():
            elapsed = datetime.now() - start_time
            live_display.update(Text.assemble(
                "Waiting for response from AI agent... (",
                (f"{elapsed.seconds}s", "magenta"),
                ")",
                justify="center"
            ))
            sleep(0.25)  # Update 4 times per second

    with Live(Text("Waiting for response from AI agent...", justify="center"), refresh_per_second=4) as live:
        display_thread = Thread(target=update_display_thread, args=(live,), daemon=True)
        display_thread.start()

        try:
            response = agent.send_message(message, system_message=system_message)
        finally:
            stop_event.set()
            display_thread.join()

        live.update(Text("Response received!", justify="center"))

    if config.debug:
        console.print("[yellow]======= Received response[/yellow]")
        print(response)
        console.print("[yellow]======= End of response[/yellow]")
    
    response_text = response.content[0].text if hasattr(response, 'content') else str(response)
    
    # Add token usage summary with detailed cache info
    if hasattr(response, 'usage'):
        usage = response.usage

        direct_input = usage.input_tokens
        cache_create = usage.cache_creation_input_tokens or 0
        cache_read = usage.cache_read_input_tokens or 0
        total_input = direct_input + cache_create + cache_read

        # Calculate percentages relative to total input
        create_pct = (cache_create / total_input * 100) if cache_create else 0
        read_pct = (cache_read / total_input * 100) if cache_read else 0
        direct_pct = (direct_input / total_input * 100) if direct_input else 0
        output_ratio = (usage.output_tokens / total_input * 100)

        # Compact single-line token usage summary
        usage_text = f"[cyan]In: [/][bold green]{total_input:,} - direct: {direct_input} ({direct_pct:.1f}%))[/] [cyan]Out:[/] [bold yellow]{usage.output_tokens:,}[/][dim]({output_ratio:.1f}%)[/]"
        if cache_create or cache_read:
            cache_text = f" [magenta]Input Cache:[/] [blue]Write:{cache_create:,}[/][dim]({create_pct:.1f}%)[/] [green]Read:{cache_read:,}[/][dim]({read_pct:.1f}%)[/]"
            usage_text += cache_text
        console.print(Rule(usage_text, style="cyan"))
    
    return response_text