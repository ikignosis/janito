from datetime import datetime
from rich.live import Live
from rich.text import Text
from rich.console import Console
from rich.rule import Rule
from rich import print
from threading import Thread
from janito.agents import agent
from .config import config
from typing import Optional


""" CACHE USAGE SUMMARY
https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
cache_creation_input_tokens: Number of tokens written to the cache when creating a new entry.
cache_read_input_tokens: Number of tokens retrieved from the cache for this request.
input_tokens: Number of input tokens which were not read from or used to create a cache.
"""

from janito.prompt import build_system_prompt

console = Console()

def progress_send_message(message: str) -> Optional[str]:
    """Send a message to the AI agent with progress indication.

    Displays a progress spinner while waiting for the agent's response and shows
    token usage statistics after receiving the response. Uses a background thread
    to update the elapsed time display.

    Args:
        message: The message to send to the AI agent

    Returns:
        Optional[str]: The response text from the AI agent, or None if interrupted

    Note:
        - Returns None if the operation is cancelled via Ctrl+C
        - If the request fails, raises the original exception
    """
    system_message = build_system_prompt()
    if config.debug:
        console.print(f"[yellow]======= Sending message via {agent.__class__.__name__.replace('AIAgent', '')}[/yellow]")
        print(system_message)
        print(message)
        console.print("[yellow]======= End of message[/yellow]")

    start_time = datetime.now()


    response = None
    error = None

    def agent_thread():
        nonlocal response, error
        try:
            response = agent.send_message(message, system_message=system_message)
        except Exception as e:
            error = e

    agent_thread = Thread(target=agent_thread, daemon=True)
    agent_thread.start()

    try:
        with Live(Text("Waiting for response from AI agent...", justify="center"), refresh_per_second=4) as live:
            while agent_thread.is_alive():
                elapsed = datetime.now() - start_time
                elapsed_seconds = elapsed.seconds
                elapsed_minutes = elapsed_seconds // 60
                remaining_seconds = elapsed_seconds % 60
                time_str = f"{elapsed_seconds}s" if elapsed_seconds < 60 else f"{elapsed_minutes}m{remaining_seconds}s"
                live.update(Text.assemble(
                    "Waiting for response from AI agent... (",
                    (time_str, "magenta"),
                    ")",
                    justify="center"
                ))
                # Check thread status every 250ms, allows for cleaner interrupts
                agent_thread.join(timeout=0.25)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
        return None

    if error:
        if isinstance(error, KeyboardInterrupt):
            console.print("\n[yellow]Operation cancelled[/yellow]")
            return None
        raise error

        elapsed = datetime.now() - start_time
        elapsed_seconds = elapsed.seconds
        elapsed_minutes = elapsed_seconds // 60
        remaining_seconds = elapsed_seconds % 60
        time_str = f"{elapsed_seconds}s" if elapsed_seconds < 60 else f"{elapsed_minutes}m{remaining_seconds}s"
        live.update(Text.assemble(
            "Response received from ",
            (agent.__class__.__name__.replace('AIAgent', ''), "dim"),
            f" in {time_str}!",
            justify="center"
        ))

    if config.debug:
        console.print("[yellow]======= Received response[/yellow]")
        print(response)
        console.print("[yellow]======= End of response[/yellow]")
    
    if hasattr(response, 'choices'):
        response_text = response.choices[0].message.content
    elif hasattr(response, 'content'):
        response_text = response.content[0].text
    else:
        response_text = str(response)

    # Add token usage summary with detailed cache info
    if hasattr(response, 'usage'):
        usage = response.usage
        
        # Handle both dict-like and object-like usage
        if isinstance(usage, dict):
            direct_input = usage.get('input_tokens', 0)
            cache_create = usage.get('cache_creation_input_tokens', 0)
            cache_read = usage.get('cache_read_input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
        else:
            direct_input = getattr(usage, 'prompt_tokens', 0)
            cache_create = 0  # Not available in new format
            cache_read = 0    # Not available in new format
            output_tokens = getattr(usage, 'completion_tokens', 0)

        total_input = direct_input + cache_create + cache_read

        # Calculate percentages relative to total input
        create_pct = (cache_create / total_input * 100) if cache_create and total_input else 0
        read_pct = (cache_read / total_input * 100) if cache_read and total_input else 0
        direct_pct = (direct_input / total_input * 100) if direct_input and total_input else 0
        output_ratio = (output_tokens / total_input * 100) if total_input else 0

        # Compact single-line token usage summary
        usage_text = f"[cyan]In: [/][bold green]{total_input:,} - direct: {direct_input} ({direct_pct:.1f}%))[/] [cyan]Out:[/] [bold yellow]{output_tokens:,}[/][dim]({output_ratio:.1f}%)[/]"

        if cache_create or cache_read:
            cache_text = f" [magenta]Input Cache:[/] [blue]Write:{cache_create:,}[/][dim]({create_pct:.1f}%)[/] [green]Read:{cache_read:,}[/][dim]({read_pct:.1f}%)[/]"
            usage_text += cache_text

        # Handle new format specific attributes
        if not isinstance(usage, dict):
            prompt_cache_hit = getattr(usage, 'prompt_cache_hit_tokens', 0)
            prompt_cache_miss = getattr(usage, 'prompt_cache_miss_tokens', 0)
            if prompt_cache_hit or prompt_cache_miss:
                cache_hit_miss_text = f" [cyan]Cache Hits:[/] [green]{prompt_cache_hit}[/] [cyan]Misses:[/] [red]{prompt_cache_miss}[/]"
                usage_text += cache_hit_miss_text

        console.print(Rule(usage_text, style="cyan"))
    
    return response_text
