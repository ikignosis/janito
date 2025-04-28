from janito.agent.rich_message_handler import RichMessageHandler
from .chat_state import load_chat_state, save_chat_state
from .chat_ui import setup_prompt_session, print_welcome_message
from .commands import handle_command
from janito.agent.conversation_exceptions import EmptyResponseError, ProviderError

# Track the active prompt session for cleanup
active_prompt_session = None


def start_chat_shell(
    profile_manager,
    continue_session=False,
    max_rounds=50,
    termweb_stdout_path=None,
    termweb_stderr_path=None,
):
    import janito.i18n as i18n
    from janito.agent.runtime_config import runtime_config

    i18n.set_locale(runtime_config.get("lang", "en"))
    global active_prompt_session
    agent = profile_manager.agent
    message_handler = RichMessageHandler()
    console = message_handler.console

    # Load state
    state = load_chat_state(continue_session)
    if termweb_stdout_path:
        state["termweb_stdout_path"] = termweb_stdout_path
    if termweb_stderr_path:
        state["termweb_stderr_path"] = termweb_stderr_path
    messages = state["messages"]
    mem_history = state["mem_history"]
    last_usage_info_ref = {"value": state["last_usage_info"]}
    last_elapsed = state["last_elapsed"]

    # Add system prompt if needed (skip in vanilla mode)
    from janito.agent.runtime_config import runtime_config

    if (
        profile_manager.system_prompt_template
        and (
            not runtime_config.get("vanilla_mode", False)
            or runtime_config.get("system_prompt_template")
        )
        and not any(m.get("role") == "system" for m in messages)
    ):
        messages.insert(0, {"role": "system", "content": agent.system_prompt_template})

    print_welcome_message(console, continued=continue_session)

    session = setup_prompt_session(
        messages, last_usage_info_ref, last_elapsed, mem_history, profile_manager, agent
    )
    active_prompt_session = session

    inject_message = state.get("inject_message")
    if "inject_message" in state:
        del state["inject_message"]

    while True:
        try:
            if inject_message is not None:
                user_input = inject_message
                inject_message = None
                was_paste_mode = False
            elif state.get("paste_mode"):
                console.print("")
                user_input = session.prompt("Multiline> ", multiline=True)
                was_paste_mode = True
                state["paste_mode"] = False
            else:
                from prompt_toolkit.formatted_text import HTML

                user_input = session.prompt(
                    HTML("<inputline>💬 </inputline>"), multiline=False
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
                        # Use <inputline> for full-line blue background, <prompt> for icon only
                        HTML(
                            "<inputline>Do you really want to exit? (y/n): </inputline>"
                        )
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

        # No need to propagate verbose; ToolExecutor and others fetch from runtime_config

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
        save_chat_state(messages, mem_history, last_usage_info_ref["value"])
