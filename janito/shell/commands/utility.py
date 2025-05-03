def handle_help(console, **kwargs):
    from janito.shell.commands import COMMAND_HANDLERS

    console.print("[bold green]Available commands:[/bold green]")
    for cmd, handler in COMMAND_HANDLERS.items():
        help_text = getattr(handler, "help_text", None)
        if help_text:
            console.print(f"  {cmd} - {help_text}")


def handle_clear(console, **kwargs):
    import os

    os.system("cls" if os.name == "nt" else "clear")


handle_clear.help_text = "Clear the terminal screen"


def handle_multi(console, shell_state=None, **kwargs):
    console.print(
        "[bold yellow]Multiline mode activated. Provide or write your text and press Esc + Enter to submit.[/bold yellow]"
    )
    if shell_state:
        shell_state.paste_mode = True


handle_multi.help_text = "Provide multiline input as next message"
