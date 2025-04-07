import os
import sys

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


COMMAND_HANDLERS = {
    "/exit": handle_exit,
    "/restart": handle_restart,
    "/paste": handle_paste,
}
