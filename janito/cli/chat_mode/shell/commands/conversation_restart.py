import os
from janito.cli.chat_mode.shell.session.manager import reset_session_id
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console


def handle_restart(shell_state=None):
    reset_session_id()
    # Conversation history is no longer saved or loaded.

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

    # Reset tool use tracker
    try:
        from janito.tooling.tool_use_tracker import ToolUseTracker

        ToolUseTracker.instance().clear_history()
    except Exception as e:
        shared_console.print(
            f"[bold yellow]Warning: Failed to reset tool use tracker:[/bold yellow] {e}"
        )

    # Reset token usage info in-place so all references (including status bar) are updated
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        shell_state.last_usage_info[k] = 0
    shell_state.last_elapsed = None

    # Reset the performance collector's last usage (so toolbar immediately reflects cleared stats)
    try:
        from janito.perf_singleton import performance_collector

        performance_collector.reset_last_request_usage()
    except Exception as e:
        shared_console.print(
            f"[bold yellow]Warning: Failed to reset PerformanceCollector token info:[/bold yellow] {e}"
        )

    # Restore tool permissions to the CLI default on restart
    try:
        from janito.tooling.permissions import (
            set_global_allowed_permissions,
            get_default_allowed_permissions,
        )
        import janito.tooling

        default_perms = get_default_allowed_permissions()
        if default_perms is not None:
            set_global_allowed_permissions(default_perms)
            janito.tooling.local_tools_adapter.set_allowed_permissions(default_perms)
            msg = None

        else:
            from janito.tooling.tool_base import ToolPermissions

            set_global_allowed_permissions(
                ToolPermissions(read=False, write=False, execute=False)
            )
            janito.tooling.local_tools_adapter.set_allowed_permissions(
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

    except Exception as e:
        shared_console.print(
            f"[yellow]Warning: Failed to restore tool permissions: {e}[/yellow]"
        )

    shared_console.print(
        "[bold green]Conversation history has been started (context reset).[/bold green]"
    )


handle_restart.help_text = "Start a new conversation (reset context)"


class RestartShellHandler(ShellCmdHandler):
    help_text = "Start a new conversation (reset context)"

    def run(self):
        handle_restart(self.shell_state)
