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

    session = PromptSession(multiline=True, key_bindings=bindings)
    session.editing_mode = EditingMode.EMACS

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
