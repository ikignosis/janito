from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler
from janito.cli.console import shared_console


class InteractiveShellHandler(ShellCmdHandler):
    help_text = "Toggle interactive mode on/off"

    def run(self):
        args = self.after_cmd_line.strip().lower()
        
        if args not in ["on", "off"]:
            shared_console.print(
                "[bold red]Usage: /interactive on|off[/bold red]"
            )
            return
        
        # Get current interactive state from shell_state if available
        current_state = getattr(self.shell_state, 'interactive_mode', True)
        
        if args == "on":
            if current_state:
                shared_console.print("[yellow]Interactive mode is already enabled.[/yellow]")
            else:
                if hasattr(self.shell_state, 'interactive_mode'):
                    self.shell_state.interactive_mode = True
                shared_console.print("[green]Interactive mode enabled.[/green]")
        elif args == "off":
            if not current_state:
                shared_console.print("[yellow]Interactive mode is already disabled.[/yellow]")
            else:
                if hasattr(self.shell_state, 'interactive_mode'):
                    self.shell_state.interactive_mode = False
                shared_console.print("[green]Interactive mode disabled.[/green]")