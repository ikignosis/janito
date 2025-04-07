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


def chat_loop(agent):
    console = Console()
    messages = []
    last_usage_info = None
    last_elapsed = None

    # Add system prompt if available
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})

    console.print("[bold green]Entering chat mode. Type /exit or /quit to exit.[/bold green]")
    console.print("[bold yellow]Use /paste for multiline input. Ctrl+D (Unix) / Ctrl+Z (Windows) to exit.[/bold yellow]")

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

    # Setup prompt_toolkit session without custom Shift+Enter multiline support
    bindings = KeyBindings()

    @bindings.add('c-r')
    def _(event):
        # Disable reverse search
        pass

    def get_toolbar():
        toolbar = (
            f'<b>/exit</b>, <b>/quit</b> to exit | '
            f'<b>/paste</b> multiline input | '
            f'Messages: {len(messages)}'
        )
        if last_usage_info:
            prompt_tokens = last_usage_info.get('prompt_tokens')
            completion_tokens = last_usage_info.get('completion_tokens')
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
            speed = None
            if last_elapsed and last_elapsed > 0:
                speed = total_tokens / last_elapsed
            toolbar += f" | Tokens: in={prompt_tokens}, out={completion_tokens}"
            if speed is not None:
                toolbar += f", speed={speed:.1f} tokens/sec"
        return HTML(toolbar)

    style = Style.from_dict({
        'bottom-toolbar': 'bg:#333333 #ffffff',
        'b': 'bold',
        'prompt': 'ansicyan bold',
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
            if user_input.strip() in ('/exit', '/quit'):
                console.print("[bold red]Exiting chat mode.[/bold red]")
                break

            if user_input.strip() == '/paste':
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
                user_input = "\n".join(pasted_lines).strip()
                if not user_input:
                    continue

            user_input = user_input.strip()
            if not user_input:
                continue

            # Save input to history
            history_list.append(user_input)
            try:
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_list, f, ensure_ascii=False, indent=2)
            except Exception as e:
                console.print(f"[red]Failed to save input history: {e}[/red]")

            messages.append({"role": "user", "content": user_input})

            def on_content(data):
                content = data.get("content", "")
                console.print(Markdown(content))

            try:
                start_time = time.time()
                content, usage_info = agent.chat(messages, on_content=on_content)
                elapsed = time.time() - start_time
                last_usage_info = usage_info
                last_elapsed = elapsed
            except Exception as e:
                console.print(f"[red]Error during chat: {e}[/red]")
                continue

        except (EOFError, KeyboardInterrupt):
            console.print("[bold red]Exiting chat mode.[/bold red]")
            break
