import sys
from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.enums import EditingMode


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

    def get_toolbar():
        return (
            "[bold cyan]/exit[/], [bold cyan]/quit[/] to exit | "
            "[bold cyan]/paste[/] multiline input | "
            "[bold cyan]Shift+Enter[/] new line | "
            "[bold cyan]Ctrl+R[/] search history"
        )

    session = PromptSession(
        multiline=True,
        key_bindings=bindings,
        editing_mode=EditingMode.EMACS,
        bottom_toolbar=get_toolbar
    )

    while True:
        try:
            try:
                user_input = session.prompt("You: ")
            except EOFError:
                print("Exiting chat mode.")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.lower() in {"/exit", "/quit"}:
                print("Exiting chat mode.")
                break

            if user_input.lower() == "/paste":
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

            messages.append({"role": "user", "content": user_input})

            def on_content(data):
                content = data.get("content", "")
                console.print(Markdown(content))

            try:
                response = agent.chat(messages, on_content=on_content)
            except Exception as e:
                console.print(f"[red]Error during chat: {e}[/red]")
                continue

        except KeyboardInterrupt:
            print("\n[Interrupted by user]")
            sys.exit(0)
