"""
/priv command handler - shows current running privileges.
"""

from .base import CmdHandler
from .registry import register_command


class PrivCmdHandler(CmdHandler):
    """Command handler for /priv command."""
    
    @property
    def name(self) -> str:
        return "/priv"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /priv command."""
        if user_input.strip().lower() == self.name.lower():
            from janito import privileges as _privileges_mod
            priv = _privileges_mod.running_privileges
            if priv is None:
                print("Privileges: (ALL allowed)")
            else:
                print(f"Privileges:")
                print(f"  READ:  {priv.READ}")
                print(f"  WRITE: {priv.WRITE}")
                print(f"  EXEC:  {priv.EXEC}")
            return True
        return False


# Register this handler
_handler = PrivCmdHandler()
register_command(_handler)
