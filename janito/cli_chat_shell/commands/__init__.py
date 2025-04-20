from .session import handle_continue, handle_history
from .system import handle_system, handle_role, handle_style
from .session_control import handle_exit, handle_restart
from .utility import handle_help, handle_clear, handle_multi
from .config import handle_reload
from .history_reset import handle_reset
from ..config_shell import handle_config_shell
from janito.agent.runtime_config import runtime_config

COMMAND_HANDLERS = {
    "/history": handle_history,
    "/continue": handle_continue,
    "/exit": handle_exit,
    "exit": handle_exit,
    "/restart": handle_restart,
    "/help": handle_help,
    "/multi": handle_multi,
    "/system": handle_system,
}

if not runtime_config.get("vanilla_mode", False):
    COMMAND_HANDLERS["/role"] = handle_role

COMMAND_HANDLERS.update(
    {
        "/clear": handle_clear,
        "/reset": handle_reset,
        "/config": handle_config_shell,
        "/reload": handle_reload,
        "/style": handle_style,
    }
)


def handle_command(command, console, **kwargs):
    parts = command.strip().split()
    cmd = parts[0]
    args = parts[1:]
    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        return handler(console, *args, **kwargs)
    console.print(
        f"[bold red]Invalid command: {cmd}. Type /help for a list of commands.[/bold red]"
    )
    return None
