def handle_view(console, args=None, shell_state=None, **kwargs):
    messages = shell_state.conversation_history.get_messages()
    if not messages:
        console.print("[yellow]Conversation history is empty.[/yellow]")
        return
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls")
        tool_call_id = msg.get("tool_call_id")
        console.print(f"[bold]{i}. {role}:[/bold] {content}")
        if tool_calls:
            console.print(f"   [cyan]tool_calls:[/cyan] {tool_calls}")
        if tool_call_id:
            console.print(f"   [magenta]tool_call_id:[/magenta] {tool_call_id}")


handle_view.help_text = "Print the current LLM conversation history"
