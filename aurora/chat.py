import sys
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style


def chat_loop(agent):
    console = Console()
    messages = []

    # Add system prompt if available
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})

    console.print("[bold green]Entering chat mode. Type /exit or /quit to exit.[/bold green]")
    console.print("[bold yellow]Use Shift+Enter for new lines. Ctrl+D (Unix) / Ctrl+Z (Windows) to exit.[/bold yellow]")

    # Setup prompt_toolkit session with multiline support
    bindings = KeyBindings()

    @bindings.add('enter')
    def _(event):
        buffer = event.current_buffer
        if buffer.complete_state:
            buffer.complete_state = None
        elif buffer.validate():
            if buffer.document.is_cursor_at_the_end:
                event.app.exit(result=buffer.text)
            else:
                buffer.insert_text('\n')

    @bindings.add('c-r')
    def _(event):
        # Disable reverse search
        pass

    def get_toolbar():
        return HTML(
            '<b>/exit</b>, <b>/quit</b> to exit | '
            '<b>/paste</b> multiline input | '
            '<b>Shift+Enter</b> new line'
        )

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
        style=style
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

            messages.append({"role": "user", "content": user_input})

            def on_content(data):
                content = data.get("content", "")
                console.print(Markdown(content))

            try:
                agent.chat(messages, on_content=on_content)
            except Exception as e:
                console.print(f"[red]Error during chat: {e}[/red]")
                continue

        except (EOFError, KeyboardInterrupt):
            console.print("[bold red]Exiting chat mode.[/bold red]")
            break
