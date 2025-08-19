import os
from prompt_toolkit.formatted_text import HTML
from janito.performance_collector import PerformanceCollector
from janito.cli.config import config
from janito import __version__ as VERSION


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


def assemble_first_line(provider_name, model_name, role, agent=None):
    cwd = os.getcwd()
    home = os.path.expanduser("~")

    # Convert to relative path if under home directory
    if cwd.startswith(home):
        cwd_display = "~" + cwd[len(home) :]
    else:
        cwd_display = cwd

    # Shorten long paths for display
    if len(cwd_display) > 50:
        cwd_display = "..." + cwd_display[-47:]

    return f" Janito {VERSION} | Provider: <provider>{provider_name}</provider> | Model: <model>{model_name}</model> | Dir: <model>{cwd_display}</model>"


def assemble_bindings_line(width, permissions=None):
    def color_state(state):
        return "on " if state == "on" else "off"

    read_state = color_state("on" if getattr(permissions, "read", False) else "off")
    write_state = color_state("on" if getattr(permissions, "write", False) else "off")
    execute_state = color_state(
        "on" if getattr(permissions, "execute", False) else "off"
    )
    return (
        f" <key-label>CTRL-C</key-label>: Interrupt/Exit | "
        f"<key-label>F2</key-label>: /restart | "
        f"<b>/help</b>: Help | "
        f"<key-label>F12</key-label>: Do It "
    )


def _get_status(shell_state):
    _support = getattr(shell_state, "_support", False)
    _status = getattr(shell_state, "_status", None)
    if not _support:
        return None
    if _status == "starting" or _status is None:
        return _status

    return _status


def _get_agent_info(agent):
    provider_name = (
        agent.get_provider_name() if hasattr(agent, "get_provider_name") else "?"
    )
    model_name = agent.get_model_name() if hasattr(agent, "get_model_name") else "?"
    role = (
        agent.template_vars.get("role", "?") if hasattr(agent, "template_vars") else "?"
    )
    return provider_name, model_name, role


def _get_permissions():
    try:
        from janito.tools.permissions import get_global_allowed_permissions

        return get_global_allowed_permissions()
    except Exception:
        return None


def get_toolbar_func(perf: PerformanceCollector, msg_count: int, shell_state):
    from prompt_toolkit.application.current import get_app

    def get_toolbar():
        width = get_app().output.get_size().columns
        agent = getattr(shell_state, "agent", None)
        this__status = _get_status(shell_state)
        provider_name, model_name, role = (
            _get_agent_info(agent) if agent is not None else ("?", "?", "?")
        )
        usage = perf.get_last_request_usage()
        first_line = assemble_first_line(provider_name, model_name, role, agent=agent)
        permissions = _get_permissions()
        bindings_line = assemble_bindings_line(width, permissions)
        toolbar_text = first_line + "\n" + bindings_line

        return HTML(toolbar_text)

    return get_toolbar
