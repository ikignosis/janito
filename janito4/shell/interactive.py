"""
Interactive shell implementation using prompt_toolkit.
"""

from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from .cmds import CmdHandler


class InteractiveShell:
    """Interactive shell for chat sessions using prompt_toolkit."""
    
    def __init__(self, model: str, commands: Optional[List["CmdHandler"]] = None):
        """
        Initialize the interactive shell.
        
        Args:
            model: The model name to display in the prompt
            commands: List of command handlers (auto-loaded if not provided)
        """
        self.model = model
        self.messages_history: List[Dict[str, Any]] = []
        self.restart_requested = False
        self.do_it_requested = False
        self.session = self._create_session()
        
        # Auto-load registered commands if not provided
        if commands is None:
            from .cmds import get_registered_commands
            self.commands = get_registered_commands()
        else:
            self.commands = commands
    
    def _create_session(self) -> PromptSession:
        """Create and configure the prompt_toolkit session."""
        kb = KeyBindings()
        
        @kb.add('f2')
        def restart_chat(event: KeyPressEvent) -> None:
            """Handle F2 key to restart conversation."""
            self.restart_requested = True
            event.app.exit(result=None)
        
        @kb.add('f12')
        def do_it_action(event: KeyPressEvent) -> None:
            """Handle F12 key to trigger 'Do It' auto-execution."""
            self.do_it_requested = True
            event.app.exit(result="Do It")
        
        return PromptSession(history=InMemoryHistory(), key_bindings=kb)
    
    def initialize_history(self, system_prompt: Optional[str] = None) -> None:
        """
        Initialize the messages history.
        
        Args:
            system_prompt: Optional system prompt to prepend
        """
        if system_prompt:
            self.messages_history = [{"role": "system", "content": system_prompt}]
        else:
            self.messages_history = []
    
    def run(
        self,
        send_prompt_func: Callable,
        verbose: bool = False,
        no_tools: bool = False
    ) -> None:
        """
        Run the interactive chat loop.
        
        Args:
            send_prompt_func: Function to call to send prompts to the AI
            verbose: Enable verbose output
            no_tools: If True, don't pass any tools to the AI
        """
        import sys
        import subprocess
        
        try:
            while True:
                self.restart_requested = False
                self.do_it_requested = False
                
                # Use HTML formatting to apply dark blue background to prompt
                prompt_text = HTML(f'<style bg="#00008b">{self.model} # </style>')
                user_input = self.session.prompt(prompt_text)
                
                # Check if F12 was pressed (Do It requested)
                if self.do_it_requested:
                    print("\n[Keybinding F12] 'Do It' to continue existing plan...")
                    user_input = "Do It"
                
                # Check if F2 was pressed (restart requested)
                if self.restart_requested:
                    self.messages_history.clear()
                    print("\n[Keybinding F2] Conversation history cleared. Starting fresh conversation.")
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    break
                if user_input.lower() == 'restart':
                    self.messages_history.clear()
                    print("Conversation history cleared. Starting fresh conversation.")
                    continue
                
                # Handle registered commands
                command_handled = False
                for cmd_handler in self.commands:
                    if cmd_handler.handle(self, user_input):
                        command_handled = True
                        break
                if command_handled:
                    continue
                
                # Handle !cmd for direct shell execution
                if user_input.startswith('!'):
                    cmd = user_input[1:].strip()
                    if cmd:
                        print(f"[Shell] Executing: {cmd}")
                        try:
                            result = subprocess.run(
                                cmd,
                                shell=True,
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            if result.stdout:
                                print(result.stdout)
                            if result.stderr:
                                print(result.stderr, file=sys.stderr)
                            print(f"[Shell] Exit code: {result.returncode}")
                        except subprocess.TimeoutExpired:
                            print("[Shell] Command timed out after 60 seconds", file=sys.stderr)
                        except Exception as e:
                            print(f"[Shell] Error: {e}", file=sys.stderr)
                    continue
                
                if user_input.strip():
                    tools_to_use = [] if no_tools else None
                    response = send_prompt_func(
                        user_input,
                        verbose=verbose,
                        previous_messages=self.messages_history,
                        tools=tools_to_use
                    )
                    # Add the user message and AI response to history
                    self.messages_history.append({"role": "user", "content": user_input})
                    if response:
                        self.messages_history.append({"role": "assistant", "content": response})
        
        except KeyboardInterrupt:
            # Prompt user for confirmation to quit
            try:
                confirm = self.session.prompt("\nDo you want to quit the conversation? (y/n): ")
                if confirm.lower().strip() in ['y', 'yes']:
                    raise EOFError()
            except (KeyboardInterrupt, EOFError):
                pass
        except EOFError:
            pass
        
        print("\nChat session ended.")
