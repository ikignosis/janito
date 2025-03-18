from typing import Optional
from typing import Tuple
import threading
import platform
import re
from janito.config import get_config
from janito.tools.usage_tracker import get_tracker
from janito.tools.rich_console import console, print_info

# Import the appropriate implementation based on the platform
if platform.system() == "Windows":
    from janito.tools.bash.win_persistent_bash import PersistentBash
else:
    from janito.tools.bash.unix_persistent_bash import PersistentBash

# Global instance of PersistentBash to maintain state between calls
_bash_session = None
_session_lock = threading.RLock()  # Use RLock to allow reentrant locking

def bash_tool(command: str, restart: Optional[bool] = False) -> Tuple[str, bool]:
    """
    Execute a bash command using a persistent Bash session.
    The appropriate implementation (Windows or Unix) is selected based on the detected platform.
    When in ask mode, only read-only commands are allowed.
    Output is printed to the console in real-time as it's received.
    
    Args:
        command: The bash command to execute
        restart: Whether to restart the bash session
        
    Returns:
        A tuple containing (output message, is_error flag)
    """
    # Import console for printing output in real-time
    from janito.tools.rich_console import console, print_info
    
    print_info(f"{command}", "Bash Run")
    global _bash_session
    
    # Check if in ask mode and if the command might modify files
    if get_config().ask_mode:
        # List of potentially modifying commands
        modifying_patterns = [
            r'\brm\b', r'\bmkdir\b', r'\btouch\b', r'\becho\b.*[>\|]', r'\bmv\b', r'\bcp\b',
            r'\bchmod\b', r'\bchown\b', r'\bsed\b.*-i', r'\bawk\b.*[>\|]', r'\bcat\b.*[>\|]',
            r'\bwrite\b', r'\binstall\b', r'\bapt\b', r'\byum\b', r'\bpip\b.*install',
            r'\bnpm\b.*install', r'\bdocker\b', r'\bkubectl\b.*apply', r'\bgit\b.*commit',
            r'\bgit\b.*push', r'\bgit\b.*merge', r'\bdd\b'
        ]
        
        # Check if command matches any modifying pattern
        for pattern in modifying_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return ("Cannot execute potentially modifying commands in ask mode. Use --ask option to disable modifications.", True)
    
    with _session_lock:
        # Initialize or restart the session if needed
        if _bash_session is None or restart:
            if _bash_session is not None:
                _bash_session.close()
            _bash_session = PersistentBash()
        
        try:
            # Execute the command - output will be printed to console in real-time
            output = _bash_session.execute(command)
            
            # Track bash command execution
            get_tracker().increment('bash_commands')
            
            # Always assume execution was successful
            is_error = False
            
            # Return the output as a string (even though it was already printed in real-time)
            return output, is_error
            
        except Exception as e:
            # Handle any exceptions that might occur
            error_message = f"Error executing bash command: {str(e)}"
            console.print(error_message, style="red bold")
            return error_message, True
