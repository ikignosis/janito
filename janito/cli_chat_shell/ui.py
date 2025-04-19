from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from janito.agent.runtime_config import runtime_config
from .session_manager import last_conversation_exists


def print_summary(console, data, continue_session):
    if not data:
        return
    msgs = data.get('messages', [])
    last_user = next((m['content'] for m in reversed(msgs) if m.get('role') == 'user'), None)
    last_assistant = next((m['content'] for m in reversed(msgs) if m.get('role') == 'assistant'), None)
    usage = data.get('last_usage_info', {})
    console.print('[bold cyan]Last saved conversation:[/bold cyan]')
    console.print(f"Messages: {len(msgs)}")
    if last_user:
        console.print(f"Last user: [italic]{last_user[:100]}{'...' if len(last_user)>100 else ''}[/italic]")
    if last_assistant:
        console.print(f"Last assistant: [italic]{last_assistant[:100]}{'...' if len(last_assistant)>100 else ''}[/italic]")
    if usage:
        ptok = usage.get('prompt_tokens')
        ctok = usage.get('completion_tokens')
        tot = (ptok or 0) + (ctok or 0)
        console.print(f"Tokens - Prompt: {ptok}, Completion: {ctok}, Total: {tot}")
    # Only print /continue suggestion if a last conversation exists
    if not continue_session and last_conversation_exists():
        console.print("[bold yellow]Type /continue to restore the last saved conversation.[/bold yellow]")


def print_welcome(console, version=None, continued=False):
    version_str = f" (v{version})" if version else ""
    vanilla_mode = runtime_config.get('vanilla_mode', False)
    if vanilla_mode:
        console.print(f"[bold magenta]Welcome to Janito{version_str} in [white on magenta]VANILLA MODE[/white on magenta]! Tools, system prompt, and temperature are disabled unless overridden.[/bold magenta]")
    else:
        console.print(f"[bold green]Welcome to Janito{version_str}! Entering chat mode. Type /exit to exit.[/bold green]")
    # Only print /continue suggestion if a last conversation exists
    if not continued and last_conversation_exists():
        console.print("[yellow]To resume your previous conversation, type /continue at any time.[/yellow]")


# ... rest of the file remains unchanged ...
