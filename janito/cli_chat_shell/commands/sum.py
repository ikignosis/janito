def handle_sum(console, shell_state=None, **kwargs):
    """
    Summarize the current chat history and replace it with a summary message.
    """
    agent = kwargs.get("agent")
    if agent is None:
        console.print("[bold red]Agent not provided to /sum command.[/bold red]")
        return

    history = shell_state.conversation_history.get_messages()
    if not history or len(history) < 2:
        console.print(
            "[bold yellow]Not enough conversation to summarize.[/bold yellow]"
        )
        return

    # Find the system message if present
    system_msg = next((m for m in history if m.get("role") == "system"), None)

    # Prepare summary prompt
    summary_prompt = {
        "role": "user",
        "content": "Summarize the following conversation in a concise paragraph for context. Only output the summary, do not include any tool calls or formatting.",
    }
    # Exclude system messages for the summary context
    convo_for_summary = [m for m in history if m.get("role") != "system"]
    summary_messages = [summary_prompt] + convo_for_summary

    try:
        summary_response = agent.chat(summary_messages, spinner=True, max_tokens=256)
        summary_text = (
            summary_response["content"]
            if isinstance(summary_response, dict)
            else str(summary_response)
        )
    except Exception as e:
        console.print(f"[bold red]Error during summarization: {e}[/bold red]")
        return

    # Rebuild conversation history
    new_history = []
    if system_msg:
        new_history.append(system_msg)
    new_history.append({"role": "assistant", "content": summary_text})
    shell_state.conversation_history.set_messages(new_history)

    console.print(
        "[bold green]Conversation summarized and history replaced with summary.[/bold green]"
    )
