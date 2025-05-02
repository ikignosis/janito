from janito.agent.rich_message_handler import RichMessageHandler
from prompt_toolkit.history import InMemoryHistory
from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from janito.shell.prompt.session_setup import (
    setup_prompt_session,
    print_welcome_message,
)
from janito.shell.commands import handle_command
from janito.agent.conversation_exceptions import EmptyResponseError, ProviderError
from janito.agent.conversation_history import ConversationHistory
from rich.console import Console


def chat_start_summary(conversation_history, console, last_usage_info):
    def format_tokens(n):
        if n is None:
            return "-"
        if n >= 1_000_000:
            return f"{n/1_000_000:.2f}m"
        elif n >= 1_000:
            return f"{n/1_000:.2f}k"
        return str(n)

    num_messages = len(conversation_history)
    roles = [m.get("role") for m in conversation_history.get_messages()]
    role_counts = {role: roles.count(role) for role in set(roles)}
    roles_str = ", ".join(
        f"[bold]{role}[/]: {count}" for role, count in role_counts.items()
    )
    stats_lines = [
        f"[cyan]Messages:[/] [bold]{num_messages}[/]",
        f"[cyan]Roles:[/] {roles_str}",
    ]
    # Use last_usage_info for tokens
    if last_usage_info:
        prompt_tokens = last_usage_info.get("prompt_tokens")
        completion_tokens = last_usage_info.get("completion_tokens")
        total_tokens = last_usage_info.get("total_tokens")
        tokens_parts = []
        if prompt_tokens is not None:
            tokens_parts.append(f"Prompt: [bold]{format_tokens(prompt_tokens)}[/]")
        if completion_tokens is not None:
            tokens_parts.append(
                f"Completion: [bold]{format_tokens(completion_tokens)}[/]"
            )
        if total_tokens is not None:
            tokens_parts.append(f"Total: [bold]{format_tokens(total_tokens)}[/]")
        if tokens_parts:
            stats_lines.append(f"[cyan]Tokens:[/] {', '.join(tokens_parts)}")

    # Add global tool usage stats
    try:
        from janito.agent.tool_use_tracker import ToolUseTracker

        tool_history = ToolUseTracker().get_history()
        if tool_history:
            from collections import Counter

            tool_counts = Counter(
                entry["tool"] for entry in tool_history if "tool" in entry
            )
            tools_str = ", ".join(
                f"[bold]{tool}[/]: {count}" for tool, count in tool_counts.items()
            )
            stats_lines.append(f"[cyan]Tools used:[/] {tools_str}")
    except Exception:
        pass  # Fail silently if tracker is unavailable

    # Print all stats in a single line, no panel
    # Print stats in a single line, but tokens info on a separate line if present
    if len(stats_lines) > 2:
        console.print(" | ".join(stats_lines[:2]))
        console.print(stats_lines[2])
        if len(stats_lines) > 3:
            console.print(" | ".join(stats_lines[3:]))
    else:
        console.print(" | ".join(stats_lines))


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
    from janito.shell.session.manager import load_conversation_by_session_id

    shell_state = ShellState()
    shell_state.profile_manager = profile_manager
    if continue_session and session_id:
        try:
            messages, prompts, usage = load_conversation_by_session_id(session_id)
        except FileNotFoundError as e:
            console.print(f"[bold red]{str(e)}[/bold red]")
            return
        # Initialize ConversationHistory with loaded messages
        shell_state.conversation_history = ConversationHistory(messages)
        conversation_history = shell_state.conversation_history
        # Always refresh the system prompt in the loaded history
        found = False
        for msg in conversation_history.get_messages():
            if msg.get("role") == "system":
                msg["content"] = profile_manager.system_prompt_template
                found = True
                break
        if not found:
            conversation_history.set_system_message(
                profile_manager.system_prompt_template
            )
        # Optionally set prompts/usage if needed
        shell_state.last_usage_info = usage or {}
    else:
        conversation_history = shell_state.conversation_history
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
            conversation_history.set_system_message(
                profile_manager.system_prompt_template
            )
    mem_history = shell_state.mem_history

    def last_usage_info_ref():
        return shell_state.last_usage_info

    last_elapsed = shell_state.last_elapsed

    print_welcome_message(console, continue_id=session_id if continue_session else None)

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

        # Clear the screen before starting LLM conversation
        console = Console()
        console.clear()

        # Print a summary of the current conversation history

        chat_start_summary(conversation_history, console, shell_state.last_usage_info)

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
