from janito.agent.rich_message_handler import RichMessageHandler
from prompt_toolkit.history import InMemoryHistory
from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from .chat_ui import setup_prompt_session, print_welcome_message
from .commands import handle_command
from janito.agent.conversation_exceptions import EmptyResponseError, ProviderError
from .session_manager import get_session_id
from janito.agent.conversation_history import ConversationHistory


@dataclass
class ShellState:
    mem_history: Any = field(default_factory=InMemoryHistory)
    conversation_history: Any = field(default_factory=lambda: ConversationHistory())
    last_usage_info: Dict[str, int] = field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    )
    last_elapsed: Optional[float] = None
    termweb_stdout_path: Optional[str] = None
    termweb_stderr_path: Optional[str] = None
    livereload_stdout_path: Optional[str] = None
    livereload_stderr_path: Optional[str] = None
    paste_mode: bool = False
    profile_manager: Optional[Any] = None


# Track the active prompt session for cleanup
active_prompt_session = None


def start_chat_shell(
    profile_manager,
    continue_session=False,
    session_id=None,
    max_rounds=100,
    termweb_stdout_path=None,
    termweb_stderr_path=None,
    livereload_stdout_path=None,
    livereload_stderr_path=None,
):
    import janito.i18n as i18n
    from janito.agent.runtime_config import runtime_config

    i18n.set_locale(runtime_config.get("lang", "en"))
    global active_prompt_session
    agent = profile_manager.agent
    message_handler = RichMessageHandler()
    console = message_handler.console

    # Print session id at start
    session_id = get_session_id()

    # Initialize state
    shell_state = ShellState()
    shell_state.profile_manager = profile_manager
    if termweb_stdout_path:
        shell_state.termweb_stdout_path = termweb_stdout_path
    if termweb_stderr_path:
        shell_state.termweb_stderr_path = termweb_stderr_path
    if livereload_stdout_path:
        shell_state.livereload_stdout_path = livereload_stdout_path
    if livereload_stderr_path:
        shell_state.livereload_stderr_path = livereload_stderr_path
    conversation_history = shell_state.conversation_history
    mem_history = shell_state.mem_history

    def last_usage_info_ref():
        return shell_state.last_usage_info

    last_elapsed = shell_state.last_elapsed

    # Add system prompt if needed (skip in vanilla mode)
    from janito.agent.runtime_config import runtime_config

    if (
        profile_manager.system_prompt_template
        and (
            not runtime_config.get("vanilla_mode", False)
            or runtime_config.get("system_prompt_template")
        )
        and not any(
            m.get("role") == "system" for m in conversation_history.get_messages()
        )
    ):
        conversation_history.set_system_message(agent.system_prompt_template)

    print_welcome_message(console, continued=continue_session)

    session = setup_prompt_session(
        lambda: conversation_history.get_messages(),
        last_usage_info_ref,
        last_elapsed,
        mem_history,
        profile_manager,
        agent,
        lambda: conversation_history,
    )
    active_prompt_session = session

    while True:
        try:
            if shell_state.paste_mode:
                console.print("")
                user_input = session.prompt("Multiline> ", multiline=True)
                was_paste_mode = True
                shell_state.paste_mode = False
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
                conversation_history.add_message(
                    {"role": "system", "content": "[Session ended by user]"}
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
                shell_state=shell_state,
            )
            if result == "exit":
                conversation_history.add_message(
                    {"role": "system", "content": "[Session ended by user]"}
                )
                break
            continue

        if not user_input.strip():
            continue

        mem_history.append_string(user_input)
        conversation_history.add_message({"role": "user", "content": user_input})

        import time

        start_time = time.time()

        # No need to propagate verbose; ToolExecutor and others fetch from runtime_config

        try:
            response = profile_manager.agent.chat(
                conversation_history,
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
        if usage:
            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                shell_state.last_usage_info[k] = usage.get(k, 0)

        # --- Ensure assistant and tool messages are added to ConversationHistory ---
        # If the last message is not an assistant/tool, add the response content
        content = response.get("content")
        if content and (
            len(conversation_history) == 0
            or conversation_history.get_messages()[-1].get("role") != "assistant"
        ):
            conversation_history.add_message({"role": "assistant", "content": content})
        # Optionally, add tool messages if present in response (extend here if needed)
        # ---------------------------------------------------------------------------

    # After exiting the main loop, print restart info if conversation has >1 message
    if len(conversation_history) > 1:
        console.print(
            f"[bold yellow]The conversation can be restarted from session id [green]{session_id}[/green][/bold yellow]"
        )
