from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from janito.agent.runtime_config import runtime_config
from janito.i18n import tr


def print_welcome(console, version=None, continue_id=None):
    version_str = f" (v{version})" if version else ""
    # DEBUG: Show continue_id/session_id at runtime
    if continue_id:
        console.print(
            f"[bold yellow]{tr('Resuming session')}[/bold yellow] [white on blue]{continue_id}[/white on blue]\n"
        )
    if runtime_config.get("vanilla_mode", False):
        console.print(
            f"[bold magenta]{tr('Welcome to Janito{version_str} in [white on magenta]VANILLA MODE[/white on magenta]! Tools, system prompt, and temperature are disabled unless overridden.', version_str=version_str)}[/bold magenta]\n"
        )
    else:
        console.print(
            f"[bold green]{tr('Welcome to Janito{version_str}! Entering chat mode. Type /exit to exit.', version_str=version_str)}[/bold green]\n"
        )


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


def assemble_first_line(model_name, role_ref, style_ref, version=None):
    version_part = f" Janito v{version}" if version else ""
    model_part = f" {tr('Model')}: <model>{model_name}</model>" if model_name else ""
    role_part = ""
    vanilla_mode = runtime_config.get("vanilla_mode", False)
    if role_ref and not vanilla_mode:
        role = role_ref()
        if role:
            role_part = f"{tr('Role')}: <role>{role}</role>"
    style_part = ""
    if style_ref:
        style = style_ref()
        if style:
            style_part = f"{tr('Style')}: <b>{style}</b>"
    first_line_parts = []
    if version_part:
        first_line_parts.append(version_part)
    if model_part:
        first_line_parts.append(model_part)
    if role_part:
        first_line_parts.append(role_part)
    if style_part:
        first_line_parts.append(style_part)
    return " | ".join(first_line_parts)


def assemble_second_line(
    width,
    last_usage_info_ref,
    history_ref,
    messages_ref,
    session_id,
    model_name,
    role_ref,
    style_ref,
):
    usage = last_usage_info_ref()
    prompt_tokens = usage.get("prompt_tokens") if usage else None
    completion_tokens = usage.get("completion_tokens") if usage else None
    total_tokens = usage.get("total_tokens") if usage else None
    msg_count = len(history_ref()) if history_ref else len(messages_ref())
    left = f" {tr('Messages')}: <msg_count>{msg_count}</msg_count>"
    tokens_part = ""
    if (
        prompt_tokens is not None
        or completion_tokens is not None
        or total_tokens is not None
    ):
        tokens_part = (
            f" | {tr('Tokens')} - {tr('Prompt')}: {format_tokens(prompt_tokens, 'tokens_in')}, "
            f"{tr('Completion')}: {format_tokens(completion_tokens, 'tokens_out')}, "
            f"{tr('Total')}: {format_tokens(total_tokens, 'tokens_total')}"
        )
    session_part = (
        f" | Session ID: <session_id>{session_id}</session_id>" if session_id else ""
    )
    second_line = f"{left}{tokens_part}{session_part}"
    total_len = len(left) + len(tokens_part) + len(session_part)
    first_line = assemble_first_line(model_name, role_ref, style_ref)
    if first_line:
        total_len += len(first_line) + 3
    if total_len < width:
        padding = " " * (width - total_len)
        second_line = f"{left}{tokens_part}{session_part}{padding}"
    return second_line


def assemble_bindings_line():
    return (
        f"<b> F12</b>: {tr('Quick Action')} | "
        f"<b>Ctrl-Y</b>: {tr('Yes')} | "
        f"<b>Ctrl-N</b>: {tr('No')} | "
        f"<b>/help</b>: {tr('Help')} | "
        f"<b>/restart</b>: {tr('Reset Conversation')}"
    )


def get_toolbar_func(
    messages_ref,
    last_usage_info_ref,
    last_elapsed_ref,
    model_name=None,
    role_ref=None,
    style_ref=None,
    version=None,
    session_id=None,
    history_ref=None,
):
    from prompt_toolkit.application.current import get_app

    def get_toolbar():
        width = get_app().output.get_size().columns
        first_line = assemble_first_line(
            model_name, role_ref, style_ref, version=version
        )
        second_line = assemble_second_line(
            width,
            last_usage_info_ref,
            history_ref,
            messages_ref,
            session_id,
            model_name,
            role_ref,
            style_ref,
        )
        bindings_line = assemble_bindings_line()
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
            "tokens_in": "ansicyan bold",
            "tokens_out": "ansigreen bold",
            "tokens_total": "ansiyellow bold",
            "msg_count": "bg:#333333 #ffff00 bold",
            "session_id": "bg:#005f00 #ffffff bold",
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
    from janito.shell.prompt.completer import ShellCommandCompleter

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
