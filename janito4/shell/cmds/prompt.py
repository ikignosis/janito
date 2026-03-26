"""
/prompt command handler - displays the current system prompt.
"""

from .base import CmdHandler
from .registry import register_command
from janito4.system_prompt import SYSTEM_PROMPT, get_system_prompt_with_skills


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
        """Print the current system prompt with skills."""
        # Get system prompt with skills advertisement
        effective_prompt = get_system_prompt_with_skills()
        
        print()
        print("=" * 60)
        print("System Prompt (with Skills)")
        print("=" * 60)
        print(effective_prompt.strip())
        print("=" * 60)
        print()


# Register this handler
_handler = PromptCmdHandler()
register_command(_handler)
