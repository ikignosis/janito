from typing import Optional
from typing import Tuple


def bash_tool(command: str, restart: Optional[bool] = False) -> Tuple[str, bool]:
    """
    A simple bash tool implementation that just prints the command and restart flag.
    
    Args:
        command: The bash command to execute
        restart: Whether to restart the process
        
    Returns:
        A tuple containing (output message, is_error flag)
    """
    # In a real implementation, this would execute the command
    # Here we just print what would be executed
    output = f"Would execute bash command: '{command}'\n"
    output += f"Restart flag is set to: {restart}"

    # Return the output with is_error=False
    return output, False