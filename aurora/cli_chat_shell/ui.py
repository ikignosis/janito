from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory


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
    if not continue_session:
        console.print("[bold yellow]Type /continue to restore the last saved conversation.[/bold yellow]")


def print_welcome(console):
    console.print("[bold green]Entering chat mode. Type /exit to exit.[/bold green]")
    console.print("[bold yellow]Press Esc+Enter to send your message.[/bold yellow]")


def get_toolbar_func(messages_ref, last_usage_info_ref, last_elapsed_ref, model_name=None):
    def format_tokens(n):
        if n is None:
            return "?"
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}m"
        if n >= 1_000:
            return f"{n/1_000:.1f}k"
        return str(n)

    def get_toolbar():
        left = (
            f'<b>/help</b> for help | <b>Submit: Esc+Enter</b> | '
            f'Messages: <msg_count>{len(messages_ref())}</msg_count>'
        )
        usage = last_usage_info_ref()
        last_elapsed = last_elapsed_ref()
        if usage:
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
            speed = None
            if last_elapsed and last_elapsed > 0:
                speed = total_tokens / last_elapsed
            left += (
                f" | Tokens: In=<tokens_in>{format_tokens(prompt_tokens)}</tokens_in> / "
                f"Out=<tokens_out>{format_tokens(completion_tokens)}</tokens_out> / "
                f"Total=<tokens_total>{format_tokens(total_tokens)}</tokens_total>"
            )
            if speed is not None:
                left += f", speed=<speed>{speed:.1f}</speed> tokens/sec"

        from prompt_toolkit.application import get_app

        if model_name:
            try:
                width = get_app().output.get_size().columns
            except Exception:
                width = 80  # fallback default
            total_len = len(left) + len(model_name) + 2  # spaces around model_name
            if total_len < width:
                padding = ' ' * (width - total_len)
                toolbar_text = f"{left}{padding} | Model: <model>{model_name}</model> "
            else:
                toolbar_text = f"{left} | Model: <model>{model_name}</model> "
        else:
            toolbar_text = left

        return HTML(toolbar_text)

    return get_toolbar


def get_prompt_session(get_toolbar_func, mem_history):
    style = Style.from_dict({
        'bottom-toolbar': 'bg:#333333 #ffffff',
        'b': 'bold',
        'prompt': 'ansicyan bold',
        'model': 'bold bg:#005f5f #ffffff',  # distinct background/foreground
        'msg_count': 'bg:#333333 #ffff00 bold',
        'tokens_in': 'ansicyan bold',
        'tokens_out': 'ansigreen bold',
        'tokens_total': 'ansiyellow bold',
        'speed': 'ansimagenta bold',
'right': 'bg:#005f5f #ffffff',
    })

    session = PromptSession(
        multiline=True,
        key_bindings=KeyBindings(),
        editing_mode=EditingMode.EMACS,
        bottom_toolbar=get_toolbar_func,
        style=style,
        history=mem_history
    )
    return session
