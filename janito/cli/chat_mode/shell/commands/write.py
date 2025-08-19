from janito.cli.console import shared_console
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler


class WriteShellHandler(ShellCmdHandler):
    help_text = "/write on|off: Enable or disable write permissions for tools. Usage: /write on or /write off."

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
            shared_console.print("[yellow]Usage: /write on|off[/yellow]")
            return
        enable = arg == "on"
        try:
            from janito.tools.permissions import (
                set_global_allowed_permissions,
                get_global_allowed_permissions,
            )
            from janito.tools.tool_base import ToolPermissions

            current = get_global_allowed_permissions()
            new_perms = ToolPermissions(
                read=current.read, write=enable, execute=current.execute
            )
            set_global_allowed_permissions(new_perms)
            # Also update the singleton tools registry permissions
            import janito.tools

            janito.tools.local_tools_adapter.set_allowed_permissions(new_perms)

        except Exception as e:
            shared_console.print(
                f"[yellow]Warning: Could not update write permissions dynamically: {e}[/yellow]"
            )
        # Refresh system prompt if agent is available
        agent = getattr(self.shell_state, "agent", None)
        if agent:
            agent.refresh_system_prompt_from_template()
            # No need to print the system prompt after permission change
        if enable:
            shared_console.print(
                "[green]Write permissions ENABLED. Tools can now write files and data.[/green]"
            )
        else:
            shared_console.print(
                "[yellow]Write permissions DISABLED. Tools cannot write files/data.[/yellow]"
            )
