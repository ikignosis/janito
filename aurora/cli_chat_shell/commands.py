import sys
import os


def handle_exit(console, **kwargs):
    console.print("[bold red]Exiting chat mode.[/bold red]")
    sys.exit(0)


def handle_restart(console, **kwargs):
    console.print("[bold yellow]Restarting CLI...[/bold yellow]")
    os.execv(sys.executable, [sys.executable] + sys.argv)


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


COMMAND_HANDLERS = {
    "/exit": handle_exit,
    "/restart": handle_restart,
    "/paste": handle_paste,
}


def handle_command(command, console, **kwargs):
    handler = COMMAND_HANDLERS.get(command)
    if handler:
        return handler(console=console, **kwargs)
    return None
