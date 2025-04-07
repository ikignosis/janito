import sys
import os
import json
import time
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from .commands import handle_command


def chat_loop(agent):
    console = Console()
    messages = []
    last_usage_info = None
    last_elapsed = None

    # Add system prompt if available
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})

    console.print("[bold green]Entering chat mode. Type /exit to exit.[/bold green]")
    console.print("[bold yellow]Press Esc+Enter to send your message.[/bold yellow]")

    # Setup persistent input history
    history_dir = os.path.join(".aurora", "input_history")
    os.makedirs(history_dir, exist_ok=True)
    today_str = datetime.now().strftime("%y%m%d")
    history_file = os.path.join(history_dir, f"{today_str}.json")

    # Load history from file
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history_list = []

    mem_history = InMemoryHistory()
    for item in history_list:
        mem_history.append_string(item)

    bindings = KeyBindings()

    @bindings.add('c-r')
    def _(event):
        pass

    def format_tokens(n):
        if n is None:
            return "?"
        if n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    def get_toolbar():
        toolbar = (
            f'<b>/help</b> for help | '
            f'Messages: <msg_count>{len(messages)}</msg_count>'
        )
        if last_usage_info:
            prompt_tokens = last_usage_info.get('prompt_tokens')
            completion_tokens = last_usage_info.get('completion_tokens')
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
            speed = None
            if last_elapsed and last_elapsed > 0:
                speed = total_tokens / last_elapsed
            toolbar += (
                f" | Tokens: in=<tokens_in>{format_tokens(prompt_tokens)}</tokens_in>, "
                f"out=<tokens_out>{format_tokens(completion_tokens)}</tokens_out>"
            )
            if speed is not None:
                toolbar += f", speed=<speed>{speed:.1f}</speed> tokens/sec"
        return HTML(toolbar)

    style = Style.from_dict({
        'bottom-toolbar': 'bg:#333333 #ffffff',
        'b': 'bold',
        'prompt': 'ansicyan bold',
        'msg_count': 'bg:#333333 #ffff00 bold',
        'tokens_in': 'ansicyan bold',
        'tokens_out': 'ansigreen bold',
        'speed': 'ansimagenta bold',
    })

    session = PromptSession(
        multiline=True,
        key_bindings=bindings,
        editing_mode=EditingMode.EMACS,
        bottom_toolbar=get_toolbar,
        style=style,
        history=mem_history
    )

    prompt_icon = HTML('<prompt>💬 </prompt>')

    while True:
        try:
            user_input = session.prompt(prompt_icon)
            stripped_input = user_input.strip()

            # Handle commands
            command_result = handle_command(stripped_input, console=console)
            if command_result is not None:
                # For /paste, replace user_input
                if isinstance(command_result, str):
                    user_input = command_result
                    if not user_input:
                        continue
                else:
                    continue

            # Prevent sending commands like /help to agent
            if stripped_input.startswith("/"):
                continue

            user_input = user_input.strip()
            if not user_input:
                # Instead of resending last message, treat empty input as 'do it'
                user_input = "do it"

            messages.append({"role": "user", "content": user_input})

            waiting_displayed = [True]
            print("Waiting for AI response...", end="", flush=True)

            def on_content(data):
                content = data.get("content", "")
                if waiting_displayed[0]:
                    sys.stdout.write("\r" + " " * len("Waiting for AI response...") + "\r")
                    sys.stdout.flush()
                    waiting_displayed[0] = False
                console.print(Markdown(content))

            start_time = time.time()
            try:
                response = agent.chat(messages, on_content=on_content)
                last_elapsed = time.time() - start_time
                last_usage_info = response.get('usage') if isinstance(response, dict) else None
            except KeyboardInterrupt:
                print("\n[Interrupted by user]")
                continue
            except Exception as e:
                print(f"[Error] {e}")
                continue

            # Save history
            mem_history.append_string(user_input)
            history_list.append(user_input)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_list, f, ensure_ascii=False, indent=2)

        except (EOFError, KeyboardInterrupt):
            console.print("\n[bold red]Exiting chat mode.[/bold red]")
            break
