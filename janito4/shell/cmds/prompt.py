"""
/prompt command handler - displays the current system prompt.
"""

from .base import CmdHandler
from .registry import register_command
from janito4.system_prompt import SYSTEM_PROMPT


class PromptCmdHandler(CmdHandler):
    """Command handler for /prompt command."""
    
    @property
    def name(self) -> str:
        return "/prompt"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /prompt command."""
        if user_input.lower() == self.name.lower():
            self._print_prompt()
            return True
        return False
    
    def _print_prompt(self) -> None:
        """Print the current system prompt."""
        print()
        print("=" * 50)
        print("System Prompt")
        print("=" * 50)
        print(SYSTEM_PROMPT.strip())
        print("=" * 50)
        print()


# Register this handler
_handler = PromptCmdHandler()
register_command(_handler)
