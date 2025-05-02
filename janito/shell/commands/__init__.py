from .session import handle_history
from .prompt import handle_prompt, handle_role
from .session_control import handle_exit
from .conversation_restart import handle_restart
from .utility import handle_help, handle_clear, handle_multi
from .termweb_log import handle_termweb_log_tail, handle_termweb_status
from .livelogs import handle_livelogs
from .sum import handle_sum
from .edit import handle_edit

from .history_view import handle_view
from janito.shell.session.config import handle_config_shell
from .verbose import handle_verbose
from .lang import handle_lang
from janito.agent.runtime_config import runtime_config

COMMAND_HANDLERS = {
    "/termweb-logs": handle_termweb_log_tail,
    "/livelogs": handle_livelogs,
    "/termweb-status": handle_termweb_status,
    "/edit": handle_edit,
    "/history": handle_history,
    "/exit": handle_exit,
    "exit": handle_exit,
    "/restart": handle_restart,
    "/start": handle_restart,
    "/help": handle_help,
    "/multi": handle_multi,
    "/prompt": handle_prompt,
    "/verbose": handle_verbose,
}

if not runtime_config.get("vanilla_mode", False):
    COMMAND_HANDLERS["/role"] = handle_role


COMMAND_HANDLERS["/lang"] = handle_lang

COMMAND_HANDLERS.update(
    {
        "/sum": handle_sum,
        "/clear": handle_clear,
        "/restart": handle_restart,
        "/config": handle_config_shell,
        "/view": handle_view,
    }
)


def handle_command(command, console, shell_state=None):
    parts = command.strip().split()
    cmd = parts[0]
    args = parts[1:]
    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        # Pass shell_state and args as keyword arguments for handlers that expect them
        return handler(console, args=args, shell_state=shell_state)
    console.print(
        f"[bold red]Invalid command: {cmd}. Type /help for a list of commands.[/bold red]"
    )
    return None
