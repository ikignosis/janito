import sys
from rich.console import Console
from rich.markdown import Markdown


def chat_loop(agent):
    console = Console()
    messages = []

    # Add system prompt if available
    if agent.system_prompt:
        messages.append({"role": "system", "content": agent.system_prompt})

    console.print("[bold green]Entering chat mode. Type /exit to quit.[/bold green]")
    console.print("[bold yellow]Enter your message. End input with a single '.' on a line or Ctrl+D (Unix) / Ctrl+Z (Windows).[/bold yellow]")

    while True:
        try:
            lines = []
            try:
                first_line = input("You: ").strip()
            except EOFError:
                print("Exiting chat mode.")
                break

            if first_line.lower() in {"/exit", "/quit"}:
                print("Exiting chat mode.")
                break
            if first_line == ".":
                continue  # ignore empty message
            lines.append(first_line)

            # Read additional lines
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if line.strip() == ".":
                    break
                lines.append(line)

            user_input = "\n".join(lines).strip()
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
