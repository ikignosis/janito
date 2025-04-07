def handle_help(console, **kwargs):
    console.print("""
[bold green]Available commands:[/bold green]
  /exit     - Exit chat mode
  /restart  - Restart the CLI
  /paste    - Paste multiline input
  /help     - Show this help message
  /system   - Show the system prompt
""")
    return True


def handle_system(console, **kwargs):
    prompt = render_system_prompt("software engineer")
    console.print(f"[bold magenta]System Prompt:[/bold magenta]\n{prompt}")
    return True


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
