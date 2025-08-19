from janito.cli.console import shared_console
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler


class ExecuteShellHandler(ShellCmdHandler):
    help_text = "/execute on|off: Enable or disable code and command execution tools. Usage: /execute on or /execute off."

    def run(self):
        if self.shell_state and getattr(self.shell_state, "no_tools_mode", False):
            shared_console.print(
                "[yellow]No tools are available in this mode (no tools, no context).[/yellow]"
            )
            return
        if not self.shell_state:
            shared_console.print("[red]Shell state unavailable.[/red]")
            return
        arg = (self.after_cmd_line or "").strip().lower()
        if arg not in ("on", "off"):
            shared_console.print("[yellow]Usage: /execute on|off[/yellow]")
            return
        enable = arg == "on"
        # Dynamically enable/disable execution tools in the registry
        try:
            from janito.tools.permissions import (
                set_global_allowed_permissions,
                get_global_allowed_permissions,
            )
            from janito.tools.tool_base import ToolPermissions

            current_perms = get_global_allowed_permissions()
            new_perms = ToolPermissions(
                read=getattr(current_perms, "read", False),
                write=getattr(current_perms, "write", False),
                execute=enable,
            )
            set_global_allowed_permissions(new_perms)
            # Also update the singleton tools registry permissions
            import janito.tools

            janito.tools.local_tools_adapter.set_allowed_permissions(new_perms)

        except Exception as e:
            shared_console.print(
                f"[yellow]Warning: Could not update execution tools dynamically: {e}[/yellow]"
            )
        # Refresh system prompt if agent is available
        agent = getattr(self.shell_state, "agent", None)
        if agent:
            agent.refresh_system_prompt_from_template()
            # No need to print the system prompt after permission change
        if enable:
            shared_console.print(
                "[green]Execution tools ENABLED. Tools can now execute code and commands.[/green]"
            )
        else:
            shared_console.print(
                "[yellow]Execution tools DISABLED. Tools cannot run code or commands.[/yellow]"
            )
