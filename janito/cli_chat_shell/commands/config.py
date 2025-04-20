def handle_reload(console, *args, **kwargs):
    from ..load_prompt import load_prompt

    agent = kwargs.get("agent")
    state = kwargs.get("state")
    filename = args[0] if args else None
    try:
        prompt_text = load_prompt(filename)
        if hasattr(agent, "system_prompt"):
            agent.system_prompt = prompt_text
        # Update the first system message in the conversation if present
        messages = state.get("messages") if state else None
        if messages:
            for msg in messages:
                if msg.get("role") == "system":
                    msg["content"] = prompt_text
                    break
        console.print(
            f"[bold green]System prompt reloaded from {'default file' if not filename else filename}![/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]Failed to reload system prompt:[/bold red] {e}")
