"""
/prompt command handler - displays the current system prompt.
"""

from .base import CmdHandler
from .registry import register_command


class PromptCmdHandler(CmdHandler):
    """Command handler for /prompt command."""
    
    @property
    def name(self) -> str:
        return "/prompt"
    
    def handle(self, shell, user_input: str) -> bool:
        """Handle the /prompt command."""
        if user_input.lower() == self.name.lower():
            self._print_prompt(shell)
            return True
        return False
    
    def _print_prompt(self, shell) -> None:
        """Print the current system prompt."""
        # Get the actual system prompt from the shell
        effective_prompt = shell.get_system_prompt()
        
        print()
        print("=" * 60)
        
        if effective_prompt is None:
            print("No system prompt is active (--no-system-prompt)")
        else:
            # Detect which prompt type is active
            if "Gmail" in effective_prompt:
                prompt_type = "Gmail Mode"
            elif "OneDrive" in effective_prompt:
                prompt_type = "OneDrive Mode"
            elif "Available Skills" in effective_prompt:
                prompt_type = "Default (with Skills)"
            else:
                prompt_type = "Default"
            
            print(f"System Prompt - {prompt_type}")
            print("=" * 60)
            print(effective_prompt.strip())
            print("=" * 60)
        
        print()


# Register this handler
_handler = PromptCmdHandler()
register_command(_handler)
