import os
import sys
from prompt_toolkit.history import InMemoryHistory
from aurora.render_prompt import render_system_prompt


def handle_exit(console, **kwargs):
    console.print("[bold red]Exiting chat mode.[/bold red]")
    sys.exit(0)


def handle_restart(console, **kwargs):
    console.print("[bold yellow]Restarting CLI...[/bold yellow]")
    os.execv(sys.executable, [sys.executable, "-m", "aurora"] + sys.argv[1:])


def handle_continue(console, state, **kwargs):
    import json, os
    save_path = os.path.join('.aurora', 'last_conversation.json')
    if not os.path.exists(save_path):
        console.print('[bold red]No saved conversation found.[/bold red]')
        return
    try:
        with open(save_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        state['messages'].clear()
        state['messages'].extend(data.get('messages', []))
        state['history_list'].clear()
        state['history_list'].extend(data.get('prompts', []))
        state['mem_history'] = InMemoryHistory()
        for item in state['history_list']:
            state['mem_history'].append_string(item)
        state['last_usage_info'] = data.get('last_usage_info')
        console.print('[bold green]Conversation restored from last session.[/bold green]')
    except Exception as e:
        console.print(f'[bold red]Failed to load conversation:[/bold red] {e}')

def handle_history(console, state, *args, **kwargs):
    messages = state.get('messages', [])
    try:
        if not args:
            # Default: last 5 messages
            start = max(0, len(messages) - 5)
            end = len(messages)
        elif len(args) == 1:
            count = int(args[0])
            start = max(0, len(messages) - count)
            end = len(messages)
        elif len(args) >= 2:
            start = int(args[0])
            end = int(args[1]) + 1  # inclusive
        else:
            start = 0
            end = len(messages)

        console.print(f"[bold cyan]Showing messages {start} to {end - 1} (total {len(messages)}):[/bold cyan]")
        for idx, msg in enumerate(messages[start:end], start=start):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            console.print(f"[bold]{idx} [{role}]:[/bold] {content}")
    except Exception as e:
        console.print(f"[bold red]Error parsing arguments or displaying history:[/bold red] {e}")

def handle_help(console, **kwargs):
    console.print("""
[bold green]Available commands:[/bold green]
  /exit     - Exit chat mode
  /restart  - Restart the CLI
  /help     - Show this help message
  /continue - Restore last saved conversation
  /reset    - Reset conversation history
  /system   - Show the system prompt
  /clear    - Clear the terminal screen
  /paste    - Paste multiline input as next message
""")


def handle_system(console, **kwargs):
    prompt = render_system_prompt("software engineer")
    console.print(f"[bold magenta]System Prompt:[/bold magenta]\n{prompt}")


def handle_clear(console, **kwargs):
    os.system('cls' if os.name == 'nt' else 'clear')


def handle_reset(console, state, **kwargs):
    import os
    save_path = os.path.join('.aurora', 'last_conversation.json')

    # Clear in-memory conversation and prompt history
    state['messages'].clear()
    state['history_list'].clear()
    state['mem_history'] = InMemoryHistory()
    state['last_usage_info'] = None
    state['last_elapsed'] = None

    # Delete saved conversation file if exists
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
            console.print('[bold yellow]Deleted saved conversation history.[/bold yellow]')
        except Exception as e:
            console.print(f'[bold red]Failed to delete saved conversation:[/bold red] {e}')
    else:
        console.print('[bold yellow]No saved conversation to delete.[/bold yellow]')

    console.print('[bold green]Conversation history has been reset.[/bold green]')


def handle_paste(console, state, **kwargs):
    console.print('[bold green]Paste mode activated. Enter your multiline input and submit when done.[/bold green]')
    state['paste_mode'] = True


COMMAND_HANDLERS = {
    "/history": handle_history,
    "/continue": handle_continue,
    "/exit": handle_exit,
    "/restart": handle_restart,

    "/help": handle_help,
    "/paste": handle_paste,
    "/system": handle_system,
    "/clear": handle_clear,
    "/reset": handle_reset,
}


def handle_command(command, console, **kwargs):
    parts = command.strip().split()
    cmd = parts[0]
    args = parts[1:]
    handler = COMMAND_HANDLERS.get(cmd)
    if handler:
        return handler(console, *args, **kwargs)
    console.print(f"[bold red]Invalid command: {cmd}. Type /help for a list of commands.[/bold red]")
    return None
