import os
import sys
from aurora.render_prompt import render_system_prompt


def handle_exit(console, **kwargs):
    console.print("[bold red]Exiting chat mode.[/bold red]")
    sys.exit(0)


def handle_restart(console, **kwargs):
    console.print("[bold yellow]Restarting CLI...[/bold yellow]")
    os.execv(sys.executable, [sys.executable, "-m", "aurora"] + sys.argv[1:])


def handle_paste(console, **kwargs):
    console.print("[bold cyan]Paste your content below. Press Ctrl+D (Unix) or Ctrl+Z (Windows) then Enter to finish.[/bold cyan]")
    pasted_lines = []
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            pasted_lines.append(line.rstrip('\n'))
    except EOFError:
        pass
    return "\n".join(pasted_lines).strip()


def handle_help(console, **kwargs):
    console.print("""
[bold green]Available commands:[/bold green]
  /exit     - Exit chat mode
  /restart  - Restart the CLI
  /paste    - Paste multiline input
  /help     - Show this help message
  /system   - Show the system prompt
""")


def handle_system(console, **kwargs):
    prompt = render_system_prompt("software engineer")
    console.print(f"[bold magenta]System Prompt:[/bold magenta]\n{prompt}")


COMMAND_HANDLERS = {
    "/exit": handle_exit,
    "/restart": handle_restart,
    "/paste": handle_paste,
    "/help": handle_help,
    "/system": handle_system,
}


def handle_command(command, console, **kwargs):
    handler = COMMAND_HANDLERS.get(command)
    if handler:
        return handler(console=console, **kwargs)
    return None
