"""
Interactive shell implementation using prompt_toolkit.
"""

from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from .cmds import CmdHandler


# History file path
HISTORY_FILE = Path.cwd() / ".janito" / "history.log"


class InteractiveShell:
    """Interactive shell for chat sessions using prompt_toolkit."""
    
    def __init__(self, model: str, commands: Optional[List["CmdHandler"]] = None, no_history: bool = False):
        """
        Initialize the interactive shell.
        
        Args:
            model: The model name to display in the prompt
            commands: List of command handlers (auto-loaded if not provided)
            no_history: If True, use in-memory history only (no file persistence)
        """
        self.model = model
        self.no_history = no_history
        self.messages_history: List[Dict[str, Any]] = []
        self.restart_requested = False
        self.do_it_requested = False
        self.exit_requested = False
        self.multiline_mode = False
        
        # Auto-load registered commands if not provided
        if commands is None:
            from .cmds import get_registered_commands
            self.commands = get_registered_commands()
        else:
            self.commands = commands
        
        # Create session after commands are loaded
        self.session = self._create_session()
    
    def _get_bottom_toolbar(self) -> list:
        """Get the bottom toolbar content."""
        tokens = []
        
        # Model info
        tokens.append(("class:model", f" model: {self.model} "))
        
        # Provider info (if available)
        try:
            from janito.general_config import get_active_provider
            provider = get_active_provider()
            if provider:
                tokens.append(("", " │ "))
                tokens.append(("class:provider", f" provider: {provider} "))
        except Exception:
            pass
        
        # Keyboard shortcuts
        tokens.append(("", " │ "))
        tokens.append(("class:key-label", "[F2] restart "))
        tokens.append(("class:key-label", "[F12] do-it "))
        tokens.append(("class:key-label", "[/exit] end "))
        tokens.append(("class:key-label", "[!cmd] shell "))
        
        # Multiline mode indicator
        if getattr(self, 'multiline_mode', False):
            tokens.append(("class:key-toggle-on", "[multi] "))
        
        return tokens
    
    def _create_session(self, multiline: bool = False) -> PromptSession:
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
        
        # Style for the chat shell
        chat_shell_style = Style.from_dict(
            {
                "prompt": "bg:#2323af #ffffff bold",
                "": "bg:#005fdd #ffffff",  # blue background for input area
                "bottom-toolbar": "fg:#232323 bg:#f0f0f0",
                "key-label": "bg:#ff9500 fg:#232323 bold",
                "provider": "fg:#117fbf",
                "model": "fg:#1f5fa9",
                "role": "fg:#e87c32 bold",
                "msg_count": "fg:#5454dd",
                "session_id": "fg:#704ab9",
                "tokens_total": "fg:#a022c7",
                "tokens_in": "fg:#00af5f",
                "tokens_out": "fg:#01814a",
                "max-tokens": "fg:#888888",
                "key-toggle-on": "bg:#ffd700 fg:#232323 bold",
                "key-toggle-off": "bg:#444444 fg:#ffffff bold",
                "cmd-label": "bg:#ff9500 fg:#232323 bold",
            }
        )
        
        # Set up history based on no_history flag
        if self.no_history:
            # In-memory only - don't persist to file
            history = InMemoryHistory()
        else:
            # Persist to file in current directory
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            history = FileHistory(str(HISTORY_FILE))
        
        return PromptSession(
            history=history,
            key_bindings=kb,
            style=chat_shell_style,
            bottom_toolbar=lambda: self._get_bottom_toolbar(),
            multiline=multiline,
        )
    
    def initialize_history(self, system_prompt: Optional[str] = None) -> None:
        """
        Initialize the messages history.
        
        Args:
            system_prompt: Optional system prompt to prepend
        """
        self._system_prompt = system_prompt
        if system_prompt:
            self.messages_history = [{"role": "system", "content": system_prompt}]
        else:
            self.messages_history = []
    
    def get_system_prompt(self) -> Optional[str]:
        """Get the current system prompt."""
        return self._system_prompt
    
    @staticmethod
    def get_history_file_path() -> Path:
        """Get the path to the history log file.
        
        Returns:
            Path: Path to ~/.janito/history.log
        """
        return HISTORY_FILE
    
    @staticmethod
    def clear_input_history() -> None:
        """Clear the input history log file."""
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
            print(f"Input history cleared from: {HISTORY_FILE}")
        else:
            print("No input history file found.")
    
    def run(
        self,
        send_prompt_func: Callable,
        verbose: bool = False,
        no_tools: bool = False,
        thinking: bool = False
    ) -> None:
        """
        Run the interactive chat loop.
        
        Args:
            send_prompt_func: Function to call to send prompts to the AI
            verbose: Enable verbose output
            no_tools: If True, don't pass any tools to the AI
            thinking: If True, enable thinking mode
        """
        import sys
        import subprocess
        
        while True:
            self.restart_requested = False
            self.do_it_requested = False
            self.exit_requested = False
            
            # Use HTML formatting for prompt
            prompt_text = HTML(f'<style bg="#00008b">{self.model} # </style>')
            
            try:
                user_input = self.session.prompt(prompt_text, multiline=self.multiline_mode)
            except KeyboardInterrupt:
                # User pressed Ctrl+C - ask to confirm quit
                try:
                    confirm = self.session.prompt("\nDo you want to quit the conversation? (y/n): ")
                    if confirm and confirm.lower().strip() in ['y', 'yes']:
                        break  # User wants to quit
                    else:
                        continue  # User doesn't want to quit, continue to next iteration
                except (KeyboardInterrupt, EOFError):
                    # User pressed Ctrl+C or Ctrl+D again during confirmation
                    break  # Quit
            except EOFError:
                # User pressed Ctrl+D at main prompt
                break
            
            # Check if F12 was pressed (Do It requested)
            if self.do_it_requested:
                print("\n[Keybinding F12] 'Do It' to continue existing plan...")
                user_input = "Do It"
            
            # Check if F2 was pressed (restart requested)
            if self.restart_requested:
                self.messages_history.clear()
                # Clear screen before printing the message
                print('\033[2J\033[H', end='')
                print("[Keybinding F2] Conversation history cleared. Starting fresh conversation.")
                continue
            
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
                # Check if exit was requested via a command
                if self.exit_requested:
                    break
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
                try:
                    response = send_prompt_func(
                        user_input,
                        verbose=verbose,
                        previous_messages=self.messages_history,
                        tools=tools_to_use,
                        thinking=thinking
                    )
                except KeyboardInterrupt:
                    print("Request interrupted")
                    response = None
                # Note: send_prompt_func already appends user and assistant messages
                # to previous_messages (which is self.messages_history), so we don't
                # need to append them here.
        
        print("\nChat session ended.")
