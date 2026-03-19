"""
/help command handler - displays all available commands.
"""

from .base import CmdHandler
from .registry import register_command, get_registered_commands


class HelpCmdHandler(CmdHandler):
    """Command handler for /help command."""
    
    @property
    def name(self) -> str:
        return "/help"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /help command."""
        if user_input.lower() == self.name.lower():
            self._print_help()
            return True
        return False
    
    def _print_help(self) -> None:
        """Print help information for all available commands."""
        commands = get_registered_commands()
        
        print()
        print("=" * 50)
        print("Available Commands")
        print("=" * 50)
        
        for cmd in commands:
            print(f"  {cmd.name}")
        
        print()
        print("Additional features:")
        print("  !<command>  - Execute a shell command directly")
        print()
        print("Keyboard shortcuts:")
        print("  [F2]        - Restart conversation")
        print("  [F12]       - Do It (continue existing plan)")
        print("=" * 50)
        print()


# Register this handler
_handler = HelpCmdHandler()
register_command(_handler)
