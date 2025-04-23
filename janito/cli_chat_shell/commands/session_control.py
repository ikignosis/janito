import os
import sys


def handle_exit(console, **kwargs):
    console.print("[bold red]Exiting chat mode.[/bold red]")
    sys.exit(0)


def handle_restart(console, **kwargs):
    console.print("[bold yellow]Restarting CLI...[/bold yellow]")
    os.execv(sys.executable, [sys.executable, "-m", "janito"] + sys.argv[1:])
