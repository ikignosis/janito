from janito.cli.console import shared_console
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler


class PrivilegesShellHandler(ShellCmdHandler):
    help_text = "Show current tool privileges or availability."

    def run(self):
        # Check for no_tools_mode in shell_state
        if self.shell_state and getattr(self.shell_state, "no_tools_mode", False):
            shared_console.print(
                "[yellow]No tools are available in this mode (no tools, no context).[/yellow]"
            )
            return
        try:
            from janito.tools.permissions import get_global_allowed_permissions

            perms = get_global_allowed_permissions()
            lines = ["[bold]Current tool privileges:[/bold]"]
            lines.append(f"Read:     {'✅' if perms.read else '❌'}")
            lines.append(f"Write:    {'✅' if perms.write else '❌'}")
            lines.append(f"Execute:  {'✅' if perms.execute else '❌'}")
            shared_console.print("\n".join(lines))
        except Exception as e:
            shared_console.print(f"[red]Error fetching privileges: {e}[/red]")
