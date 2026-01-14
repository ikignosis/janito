import sys


def handle_exit(**kwargs):
    console.print("[bold red]Exiting chat mode.[/bold red]")
    sys.exit(0)


handle_exit.help_text = "Exit chat mode"
