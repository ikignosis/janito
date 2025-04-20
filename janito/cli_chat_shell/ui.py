from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from janito.agent.runtime_config import runtime_config
from .session_manager import last_conversation_exists


def print_summary(console, data, continue_session):
    if not data:
        return
    msgs = data.get("messages", [])
    last_user = next(
        (m["content"] for m in reversed(msgs) if m.get("role") == "user"), None
    )
    last_assistant = next(
        (m["content"] for m in reversed(msgs) if m.get("role") == "assistant"), None
    )
    usage = data.get("last_usage_info", {})
    console.print("[bold cyan]Last saved conversation:[/bold cyan]")
    console.print(f"Messages: {len(msgs)}")
    if last_user:
        console.print(
            f"Last user: [italic]{last_user[:100]}{'...' if len(last_user)>100 else ''}[/italic]"
        )
    if last_assistant:
        console.print(
            f"Last assistant: [italic]{last_assistant[:100]}{'...' if len(last_assistant)>100 else ''}[/italic]"
        )
    if usage:
        ptok = usage.get("prompt_tokens")
        ctok = usage.get("completion_tokens")
        tot = (ptok or 0) + (ctok or 0)
        console.print(f"Tokens - Prompt: {ptok}, Completion: {ctok}, Total: {tot}")
    # Only print /continue suggestion if a last conversation exists
    if not continue_session and last_conversation_exists():
        console.print(
            "[bold yellow]Type /continue to restore the last saved conversation.[/bold yellow]"
        )


def print_welcome(console, version=None, continued=False):
    version_str = f" (v{version})" if version else ""
    vanilla_mode = runtime_config.get("vanilla_mode", False)
    if vanilla_mode:
        console.print(
            f"[bold magenta]Welcome to Janito{version_str} in [white on magenta]VANILLA MODE[/white on magenta]! Tools, system prompt, and temperature are disabled unless overridden.[/bold magenta]\n[cyan]Almost there! Press F12 to proceed (but double-check what is proposed) 😊[/cyan]"
        )
    else:
        console.print(
            f"[bold green]Welcome to Janito{version_str}! Entering chat mode. Type /exit to exit.[/bold green]\n[cyan]Almost there! Press F12 to proceed (but double-check what is proposed) 😊[/cyan]"
        )
    # Only print /continue suggestion if a last conversation exists


def get_toolbar_func(
    messages_ref,
    last_usage_info_ref,
    last_elapsed_ref,
    model_name=None,
    role_ref=None,
    style_ref=None,
):
    def format_tokens(n):
        if n is None:
            return "?"
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}m"
        if n >= 1_000:
            return f"{n/1_000:.1f}k"
        return str(n)

    def get_toolbar():
        left = f" Messages:  <msg_count>{len(messages_ref())}</msg_count>"
        usage = last_usage_info_ref()
        last_elapsed = last_elapsed_ref()
        if usage:
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
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

        width = get_app().output.get_size().columns
        model_part = f" Model:  <model>{model_name}</model>" if model_name else ""
        role_part = ""
        vanilla_mode = runtime_config.get("vanilla_mode", False)
        if role_ref and not vanilla_mode:
            role = role_ref()
            if role:
                role_part = f"Role: <b>{role}</b>"
        style_part = ""
        if style_ref:
            style = style_ref()
            if style:
                style_part = f"Style: <b>{style}</b>"
        first_line_parts = []
        if model_part:
            first_line_parts.append(model_part)
        if role_part:
            first_line_parts.append(role_part)
        if style_part:
            first_line_parts.append(style_part)
        first_line = " | ".join(first_line_parts)
        help_part = "<b>/help</b> for help | <b>F12</b>: proceed"
        total_len = len(left) + len(help_part) + 3  # separators and spaces
        if first_line:
            total_len += len(first_line) + 3
        if total_len < width:
            padding = " " * (width - total_len)
            second_line = f"{left}{padding} | {help_part}"
        else:
            second_line = f"{left} | {help_part}"
        if first_line:
            toolbar_text = first_line + "\n" + second_line
        else:
            toolbar_text = second_line
        return HTML(toolbar_text)

    return get_toolbar


def get_prompt_session(get_toolbar_func, mem_history):
    from prompt_toolkit.key_binding import KeyBindings

    style = Style.from_dict(
        {
            "bottom-toolbar": "bg:#333333 #ffffff",
            "b": "bold",
            "prompt": "bold bg:#000080 #ffffff",
            "model": "bold bg:#005f5f #ffffff",  # distinct background/foreground
            "msg_count": "bg:#333333 #ffff00 bold",
            "tokens_in": "ansicyan bold",
            "tokens_out": "ansigreen bold",
            "tokens_total": "ansiyellow bold",
            "speed": "ansimagenta bold",
            "right": "bg:#005f5f #ffffff",
            "input": "bg:#000080 #ffffff",
            "": "bg:#000080 #ffffff",
        }
    )
    kb = KeyBindings()

    @kb.add("f12")
    def _(event):
        """When F12 is pressed, send 'proceed' as input immediately."""
        buf = event.app.current_buffer
        buf.text = "proceed"
        buf.validate_and_handle()

    session = PromptSession(
        multiline=False,
        key_bindings=kb,
        editing_mode=EditingMode.EMACS,
        bottom_toolbar=get_toolbar_func,
        style=style,
        history=mem_history,
    )
    return session


# ... rest of the file remains unchanged ...
