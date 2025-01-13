from typing import Optional
from rich.console import Console
from janito.cli.commands import handle_request
from janito.shell.user_prompt import prompt_user

console = Console()

def shell_loop():
    """Main shell loop for handling user requests.

    The shell can be exited using:
    - typing '/exit'
    - pressing Ctrl+D
    """
    while True:
        request = prompt_user("Enter change request (type '/exit' to quit)").strip()
        if request.lower() == '/exit':
            break
        if request:
            handle_request(request)
