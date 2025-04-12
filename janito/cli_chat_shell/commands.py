import os
import sys
import json
from prompt_toolkit.history import InMemoryHistory
from janito.render_prompt import render_system_prompt
from .load_prompt import load_prompt
from janito.agent.config import effective_config


def handle_exit(console, **kwargs):
    console.print("[bold red]Exiting chat mode.[/bold red]")
    sys.exit(0)


def handle_restart(console, **kwargs):
    console.print("[bold yellow]Restarting CLI...[/bold yellow]")
    os.execv(sys.executable, [sys.executable, "-m", "janito"] + sys.argv[1:])


def handle_continue(console, state, **kwargs):
    save_path = os.path.join('.janito', 'last_conversation.json')
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
  /role     - Change the system role
  /clear    - Clear the terminal screen
  /multi    - Provide multiline input as next message
""")


def handle_reload(console, *args, **kwargs):
    """
    /reload [filename] - Reload the system prompt from the default or specified file
    """
    agent = kwargs.get('agent')
    state = kwargs.get('state')
    filename = args[0] if args else None
    try:
        prompt_text = load_prompt(filename)
        if hasattr(agent, 'system_prompt'):
            agent.system_prompt = prompt_text
        # Update the first system message in the conversation if present
        messages = state.get('messages') if state else None
        if messages:
            for msg in messages:
                if msg.get('role') == 'system':
                    msg['content'] = prompt_text
                    break
        console.print(f"[bold green]System prompt reloaded from {'default file' if not filename else filename}![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to reload system prompt:[/bold red] {e}")


def handle_system(console, **kwargs):
    prompt = getattr(kwargs.get('agent'), 'system_prompt', None)
    if not prompt:
        prompt = render_system_prompt("software engineer")
    console.print(f"[bold magenta]System Prompt:[/bold magenta]\n{prompt}")


def handle_clear(console, **kwargs):
    os.system('cls' if os.name == 'nt' else 'clear')


def handle_reset(console, state, **kwargs):
    import os
    save_path = os.path.join('.janito', 'last_conversation.json')

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


def handle_multi(console, state, **kwargs):
    console.print("[bold yellow]Multiline mode activated. Provide or write your text and press Esc + Enter to submit.[/bold yellow]")
    state['paste_mode'] = True

from janito.agent.runtime_config import runtime_config
from .config_shell import handle_config_shell

def handle_role(console, *args, **kwargs):
    state = kwargs.get('state')
    agent = kwargs.get('agent')
    if not args:
        console.print('[bold red]Usage: /role <new role description>[/bold red]')
        return
    new_role = ' '.join(args)
    # Update system message in conversation
    found = False
    for msg in state['messages']:
        if msg.get('role') == 'system':
            msg['content'] = render_system_prompt(new_role)
            found = True
            break
    if not found:
        # Insert new system message at the beginning
        state['messages'].insert(0, {'role': 'system', 'content': new_role})
    # Update agent's system prompt attribute if exists
    if hasattr(agent, 'system_prompt'):
        agent.system_prompt = render_system_prompt(new_role)
    # Also store the raw role string
    if hasattr(agent, 'role_name'):
        agent.role_name = new_role
    else:
        setattr(agent, 'role_name', new_role)
    # Update runtime config so all lookups see the new role
    runtime_config.set('role', new_role)
    console.print(f"[bold green]System role updated to:[/bold green] {new_role}")


COMMAND_HANDLERS = {
    "/history": handle_history,
    "/continue": handle_continue,
    "/exit": handle_exit,
    "/restart": handle_restart,

    "/help": handle_help,
    "/multi": handle_multi,
    "/system": handle_system,
    "/role": handle_role,
    "/clear": handle_clear,
    "/reset": handle_reset,
    "/config": handle_config_shell,
    "/reload": handle_reload,
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
