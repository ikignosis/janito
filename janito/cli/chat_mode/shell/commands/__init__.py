from .base import ShellCmdHandler
from .history_view import ViewShellHandler
from .lang import LangShellHandler
from .provider import ProviderCmdHandler

from .prompt import PromptShellHandler, RoleShellHandler
from .multi import MultiShellHandler
from .model import ModelShellHandler
from .role import RoleCommandShellHandler
from .session import HistoryShellHandler
from .tools import ToolsShellHandler
from .help import HelpShellHandler
from .security_command import SecurityCommand
from janito.cli.console import shared_console

COMMAND_HANDLERS = {
    # Bang handler for shell commands
    "!": __import__(
        "janito.cli.chat_mode.shell.commands.bang", fromlist=["BangShellHandler"]
    ).BangShellHandler,
    "/execute": __import__(
        "janito.cli.chat_mode.shell.commands.execute", fromlist=["ExecuteShellHandler"]
    ).ExecuteShellHandler,
    "/read": __import__(
        "janito.cli.chat_mode.shell.commands.read", fromlist=["ReadShellHandler"]
    ).ReadShellHandler,
    "/write": __import__(
        "janito.cli.chat_mode.shell.commands.write", fromlist=["WriteShellHandler"]
    ).WriteShellHandler,
    "/clear": __import__(
        "janito.cli.chat_mode.shell.commands.clear", fromlist=["ClearShellHandler"]
    ).ClearShellHandler,
    "/restart": __import__(
        "janito.cli.chat_mode.shell.commands.conversation_restart",
        fromlist=["RestartShellHandler"],
    ).RestartShellHandler,
    "/view": ViewShellHandler,
    "/lang": LangShellHandler,
    "/prompt": PromptShellHandler,
    "/role": RoleShellHandler,
    "/history": HistoryShellHandler,
    "/tools": ToolsShellHandler,
    "/model": ModelShellHandler,
    "/multi": MultiShellHandler,
    "/help": HelpShellHandler,
    "/security": SecurityCommand,
    "/provider": ProviderCmdHandler,
}


def get_shell_command_names():
    return sorted(cmd for cmd in COMMAND_HANDLERS.keys() if cmd.startswith("/"))


def handle_command(command, shell_state=None):
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0]
    after_cmd_line = parts[1] if len(parts) > 1 else ""
    handler_cls = COMMAND_HANDLERS.get(cmd)
    if handler_cls:
        handler = handler_cls(after_cmd_line=after_cmd_line, shell_state=shell_state)
        return handler.run()
    shared_console.print(
        f"[bold red]Invalid command: {cmd}. Type /help for a list of commands.[/bold red]"
    )
    return None
