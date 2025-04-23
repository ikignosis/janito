from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.key_binding import KeyBindings
from janito.agent.runtime_config import runtime_config


def print_summary(console, data, continue_session):
    pass  # unchanged


def print_welcome(
    console, profile_manager=None, vanilla_mode=None, version=None, continued=None
):
    msg = "[bold green]Welcome to Janito!"
    if version:
        msg += f" (v{version})"
    msg += "[/bold green]"
    if continued:
        msg += "\n[dim]Session continued.[/dim]"
    console.print(msg)


def get_toolbar_func(
    messages_ref,
    last_usage_info_ref,
    last_elapsed_ref,
    model_name=None,
    role_ref=None,
    style_ref=None,
    profile_ref=None,
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
        profile_part = ""
        vanilla_mode = runtime_config.get("vanilla_mode", False)
        if role_ref and not vanilla_mode:
            role = role_ref()
            if role:
                role_part = f"Role: <b>{role}</b>"
        if profile_ref and not vanilla_mode:
            profile = profile_ref()
            if profile:
                profile_part = f"Profile: <b>{profile}</b>"
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
        if profile_part:
            first_line_parts.append(profile_part)
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


def get_f12_key_bindings():
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

    return bindings


def get_prompt_session(get_toolbar_func, mem_history):
    style = Style.from_dict(
        {
            # Toolbar style
            "bottom-toolbar": "bg:#333333 #ffffff",
        }
    )
    return PromptSession(
        bottom_toolbar=get_toolbar_func,
        style=style,
        editing_mode=EditingMode.VI,
        key_bindings=get_f12_key_bindings(),
        history=mem_history,
    )
