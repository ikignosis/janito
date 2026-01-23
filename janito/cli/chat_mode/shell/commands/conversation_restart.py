import os
from janito.cli.chat_mode.shell.session.manager import reset_session_id
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console
from janito.tooling.tool_use_tracker import ToolUseTracker
from janito.tooling.permissions import (
        set_global_allowed_permissions,
        get_default_allowed_permissions,
    )
import janito.tooling
from janito.tools.local import get_local_tools_adapter
from janito.perf_singleton import performance_collector

def handle_restart(shell_state=None):
    reset_session_id()


    # Clear the terminal screen
    shared_console.clear()

    # Reset conversation history using the agent's method
    if hasattr(shell_state, "agent") and shell_state.agent:
        shell_state.agent.reset_conversation_history()
        # Reset system prompt to original template context if available
        if hasattr(shell_state.agent, "_original_template_vars"):
            shell_state.agent._template_vars = (
                shell_state.agent._original_template_vars.copy()
            )
        shell_state.agent.refresh_system_prompt_from_template()
        # No need to print the system prompt after restart


    # Reset token usage info in-place so all references (including status bar) are updated
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        shell_state.last_usage_info[k] = 0
    shell_state.last_elapsed = None

    # Reset the performance collector's last usage (so toolbar immediately reflects cleared stats)
    performance_collector.reset_last_request_usage()

    default_perms = get_default_allowed_permissions()
    if default_perms is not None:
        set_global_allowed_permissions(default_perms)
        tools_adapter = get_default_allowed_permissions()
        tools_adapter.set_allowed_permissions(default_perms)
        msg = None

    else:
        from janito.tooling.tool_base import ToolPermissions

        set_global_allowed_permissions(
            ToolPermissions(read=False, write=False, execute=False)
        )
        tools_adapter = get_local_tools_adapter()
        tools_adapter.set_allowed_permissions(
            ToolPermissions(read=False, write=False, execute=False)
        )
        msg = "[green]All tool permissions have been set to OFF (read, write, execute = False).[/green]"
    # Refresh system prompt to reflect new permissions
    if (
        hasattr(shell_state, "agent")
        and shell_state.agent
        and hasattr(shell_state.agent, "refresh_system_prompt_from_template")
    ):
        shell_state.agent.refresh_system_prompt_from_template()
    if msg:
        shared_console.print(msg)


    # Clear the user tracker history
    ToolUseTracker.instance().clear_history()

    shared_console.print(
        "[bold green]Conversation history has been started (context reset).[/bold green]"
    )


handle_restart.help_text = "Start a new conversation (reset context)"


class RestartShellHandler(ShellCmdHandler):
    help_text = "Start a new conversation (reset context)"

    def run(self):
        handle_restart(self.shell_state)
