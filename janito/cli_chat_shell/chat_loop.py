from janito.agent.rich_message_handler import RichMessageHandler
from .chat_state import load_chat_state
from .chat_ui import setup_prompt_session, print_welcome_message
from .commands import handle_command
from janito.agent.conversation_exceptions import EmptyResponseError, ProviderError


def start_chat_shell(profile_manager, continue_session=False, max_rounds=50):
    agent = profile_manager.agent
    message_handler = RichMessageHandler()
    console = message_handler.console

    # Load state
    state = load_chat_state(continue_session)
    messages = state["messages"]
    mem_history = state["mem_history"]
    last_usage_info_ref = {"value": state["last_usage_info"]}
    last_elapsed = state["last_elapsed"]

    # Add system prompt if needed
    if profile_manager.system_prompt_template and not any(
        m.get("role") == "system" for m in messages
    ):
        messages.insert(0, {"role": "system", "content": agent.system_prompt_template})

    print_welcome_message(console, continued=continue_session)

    session = setup_prompt_session(
        messages, last_usage_info_ref, last_elapsed, mem_history, profile_manager, agent
    )

    while True:
        try:
            if state.get("paste_mode"):
                console.print("")
                user_input = session.prompt("Multiline> ", multiline=True)
                was_paste_mode = True
                state["paste_mode"] = False
            else:
                from prompt_toolkit.formatted_text import HTML

                user_input = session.prompt(
                    HTML("<prompt>💬 </prompt>"), multiline=False
                )
                was_paste_mode = False
        except EOFError:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except KeyboardInterrupt:
            console.print()  # Move to next line
            try:
                confirm = (
                    session.prompt(
                        HTML("<prompt>Do you really want to exit? (y/n): </prompt>")
                    )
                    .strip()
                    .lower()
                )
            except KeyboardInterrupt:
                message_handler.handle_message(
                    {"type": "error", "message": "Exiting..."}
                )
                break
            if confirm == "y":
                message_handler.handle_message(
                    {"type": "error", "message": "Exiting..."}
                )
                break
            else:
                continue

        cmd_input = user_input.strip().lower()
        if not was_paste_mode and (cmd_input.startswith("/") or cmd_input == "exit"):
            # Treat both '/exit' and 'exit' as commands
            result = handle_command(
                user_input.strip(),
                console,
                profile_manager=profile_manager,
                agent=agent,
                messages=messages,
                mem_history=mem_history,
                state=state,
            )
            if result == "exit":
                break
            continue

        if not user_input.strip():
            continue

        mem_history.append_string(user_input)
        messages.append({"role": "user", "content": user_input})

        import time

        start_time = time.time()

        try:
            response = profile_manager.agent.chat(
                messages,
                max_rounds=max_rounds,
                message_handler=message_handler,
                spinner=True,
            )
        except KeyboardInterrupt:
            message_handler.handle_message(
                {"type": "info", "message": "Request interrupted. Returning to prompt."}
            )
            continue
        except ProviderError as e:
            message_handler.handle_message(
                {"type": "error", "message": f"Provider error: {e}"}
            )
            continue
        except EmptyResponseError as e:
            message_handler.handle_message({"type": "error", "message": f"Error: {e}"})
            continue
        last_elapsed = time.time() - start_time

        usage = response.get("usage")
        last_usage_info_ref["value"] = usage

        # Save conversation and input history
        # save_chat_state(messages, mem_history, last_usage_info)
