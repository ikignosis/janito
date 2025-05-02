import os


from janito.shell.session.manager import reset_session_id


def handle_restart(console, shell_state=None, **kwargs):
    from janito.shell.session.manager import load_last_conversation, save_conversation

    reset_session_id()
    save_path = os.path.join(".janito", "last_conversation.json")

    # --- Append end-of-conversation message to old history if it exists and is non-trivial ---
    if os.path.exists(save_path):
        try:
            messages, prompts, usage = load_last_conversation(save_path)
            if messages and (
                len(messages) > 1
                or (len(messages) == 1 and messages[0].get("role") != "system")
            ):
                messages.append(
                    {"role": "system", "content": "[Session ended by user]"}
                )
                # Save to permanent chat history (let save_conversation pick session file)
                save_conversation(messages, prompts, usage)
        except Exception as e:
            console.print(
                f"[bold red]Failed to update previous conversation history:[/bold red] {e}"
            )

    # Clear the terminal screen
    console.clear()

    # Reset conversation history using its clear method
    shell_state.conversation_history.clear()

    # Reset tool use tracker
    try:
        from janito.agent.tool_use_tracker import ToolUseTracker

        ToolUseTracker.instance().clear_history()
    except Exception as e:
        console.print(
            f"[bold yellow]Warning: Failed to reset tool use tracker:[/bold yellow] {e}"
        )
    # Set system prompt from agent template if available
    if (
        hasattr(shell_state, "profile_manager")
        and shell_state.profile_manager
        and hasattr(shell_state.profile_manager, "agent")
        and shell_state.profile_manager.agent
        and getattr(shell_state.profile_manager.agent, "system_prompt_template", None)
        and not any(
            m.get("role") == "system"
            for m in shell_state.conversation_history.get_messages()
        )
    ):
        shell_state.conversation_history.set_system_message(
            shell_state.profile_manager.agent.system_prompt_template
        )

    # Reset token usage info in-place so all references (including status bar) are updated
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if k in shell_state.last_usage_info:
            shell_state.last_usage_info[k] = 0
        else:
            shell_state.last_usage_info[k] = 0
    shell_state.last_elapsed = None

    console.print(
        "[bold green]Conversation history has been started (context reset).[/bold green]"
    )
