from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from janito.agent.runtime_config import runtime_config


def print_summary(console, data, continue_session):
    if not data:
        return
    console.print("[bold cyan]Last saved conversation:[/bold cyan]")


def print_welcome(console, version=None, continued=False):
    version_str = f" (v{version})" if version else ""
    if runtime_config.get("vanilla_mode", False):
        console.print(
            f"[bold magenta]Welcome to Janito{version_str} in [white on magenta]VANILLA MODE[/white on magenta]! Tools, system prompt, and temperature are disabled unless overridden.[/bold magenta]\n"
            f"[cyan] F12 = Quick Action (follows the recommended action).[/cyan]"
        )
    else:
        console.print(
            f"[bold green]Welcome to Janito{version_str}! Entering chat mode. Type /exit to exit.[/bold green]\n"
            f"[cyan] F12 = Quick Action (follows the recommended action).[/cyan]"
        )


def get_toolbar_func(
    messages_ref,
    last_usage_info_ref,
    last_elapsed_ref,
    model_name=None,
    role_ref=None,
    style_ref=None,
    profile_ref=None,
    version=None,
):
    from prompt_toolkit.application.current import get_app

    def format_tokens(n, tag=None):
        if n is None:
            return "?"
        if n < 1000:
            val = str(n)
        elif n < 1000000:
            val = f"{n/1000:.1f}k"
        else:
            val = f"{n/1000000:.1f}M"
        return f"<{tag}>{val}</{tag}>" if tag else val

    def get_toolbar():
        width = get_app().output.get_size().columns
        model_part = f" Model: <model>{model_name}</model>" if model_name else ""
        role_part = ""
        profile_part = ""
        vanilla_mode = runtime_config.get("vanilla_mode", False)
        if role_ref and not vanilla_mode:
            role = role_ref()
            if role:
                role_part = f"Role: <role>{role}</role>"
        if profile_ref and not vanilla_mode:
            profile = profile_ref()
            if profile:
                profile_part = f"Profile: <profile>{profile}</profile>"
        style_part = ""
        if style_ref:
            style = style_ref()
            if style:
                style_part = f"Style: <b>{style}</b>"
        usage = last_usage_info_ref()
        prompt_tokens = usage.get("prompt_tokens") if usage else None
        completion_tokens = usage.get("completion_tokens") if usage else None
        total_tokens = usage.get("total_tokens") if usage else None
        first_line_parts = []
        if model_part:
            first_line_parts.append(model_part)
        if profile_part:
            first_line_parts.append(profile_part)
        if role_part:
            first_line_parts.append(role_part)
        if style_part:
            first_line_parts.append(style_part)
        first_line = " | ".join(first_line_parts)
        left = f" Messages: <msg_count>{len(messages_ref())}</msg_count>"
        tokens_part = ""
        if (
            prompt_tokens is not None
            or completion_tokens is not None
            or total_tokens is not None
        ):
            tokens_part = (
                f" | Tokens - Prompt: {format_tokens(prompt_tokens, 'tokens_in')}, "
                f"Completion: {format_tokens(completion_tokens, 'tokens_out')}, "
                f"Total: {format_tokens(total_tokens, 'tokens_total')}"
            )
        # Move /help and /start tips to key bindings/info line
        # Compose second/status line (no help_part)
        second_line = f"{left}{tokens_part}"
        total_len = len(left) + len(tokens_part)
        if first_line:
            total_len += len(first_line) + 3
        if total_len < width:
            padding = " " * (width - total_len)
            second_line = f"{left}{tokens_part}{padding}"
        # Add key bindings info as an extra line, now including /help and /start
        bindings_line = "<b> F12</b>: Quick Action | <b>Ctrl-Y</b>: Yes | <b>Ctrl-N</b>: No | <b>/help</b>: Help | <b>/start</b>: New Task"
        if first_line:
            toolbar_text = first_line + "\n" + second_line + "\n" + bindings_line
        else:
            toolbar_text = second_line + "\n" + bindings_line
        return HTML(toolbar_text)

    return get_toolbar


def get_custom_key_bindings():
    """
    Returns prompt_toolkit KeyBindings for custom CLI shortcuts:
    - F12: Cycles through quick action phrases and submits.
    - Ctrl-Y: Inserts 'Yes' and submits (for confirmation prompts).
    - Ctrl-N: Inserts 'No' and submits (for confirmation prompts).
    """
    bindings = KeyBindings()
    _f12_instructions = ["proceed", "go ahead", "continue", "next", "okay"]
    _f12_index = {"value": 0}

    @bindings.add("f12")
    def _(event):
        buf = event.app.current_buffer
        idx = _f12_index["value"]
        buf.text = _f12_instructions[idx]
        buf.validate_and_handle()
        _f12_index["value"] = (idx + 1) % len(_f12_instructions)

    @bindings.add("c-y")
    def _(event):
        buf = event.app.current_buffer
        buf.text = "Yes"
        buf.validate_and_handle()

    @bindings.add("c-n")
    def _(event):
        buf = event.app.current_buffer
        buf.text = "No"
        buf.validate_and_handle()

    return bindings


def get_prompt_session(get_toolbar_func, mem_history):
    style = Style.from_dict(
        {
            "bottom-toolbar": "bg:#333333 #ffffff",
            "model": "bold bg:#005f5f #ffffff",
            "role": "bold ansiyellow",
            "profile": "bold ansiyellow",
            "tokens_in": "ansicyan bold",
            "tokens_out": "ansigreen bold",
            "tokens_total": "ansiyellow bold",
            "msg_count": "bg:#333333 #ffff00 bold",
            "b": "bold",
            "prompt": "bg:#005f5f #ffffff",  # (legacy, not used)
            # Style for prompt_toolkit input line:
            #   - '': affects the actual user input area background (full line, most reliable)
            #   - "input-field": also affects the input area in some prompt_toolkit versions
            #   - <inputline> tag: only affects the prompt label, not the input area
            "": "bg:#005fdd #ffffff",  # Blue background for the user input area (recommended)
            "input-field": "bg:#005fdd #ffffff",  # Blue background for the user input area (optional)
            "inputline": "bg:#005fdd #ffffff",  # Blue background for the prompt label (icon/text)
        }
    )
    from .shell_command_completer import ShellCommandCompleter

    completer = ShellCommandCompleter()
    return PromptSession(
        bottom_toolbar=get_toolbar_func,
        style=style,
        editing_mode=EditingMode.VI,
        key_bindings=get_custom_key_bindings(),
        history=mem_history,
        completer=completer,
    )


def _(text):
    return text
