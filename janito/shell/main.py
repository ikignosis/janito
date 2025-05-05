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
from janito.agent.api_exceptions import ApiError
from janito.agent.llm_conversation_history import LLMConversationHistory
import janito.i18n as i18n
from janito.agent.runtime_config import runtime_config
from rich.console import Console
import os
from janito.shell.session.manager import get_session_id
from prompt_toolkit.formatted_text import HTML
import time
from janito.shell.input_history import UserInputHistory


@dataclass
class ShellState:
    mem_history: Any = field(default_factory=InMemoryHistory)
    conversation_history: Any = field(default_factory=lambda: LLMConversationHistory())
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
    user_input_history: Optional[Any] = None


# Track the active prompt session for cleanup
active_prompt_session = None


def load_session(shell_state, continue_session, session_id, profile_manager):
    from janito.shell.session.manager import load_conversation_by_session_id

    if continue_session and session_id:
        try:
            messages, prompts, usage = load_conversation_by_session_id(session_id)
        except FileNotFoundError as e:
            shell_state.profile_manager.agent.message_handler.console.print(
                f"[bold red]{str(e)}[/bold red]"
            )
            return False
        shell_state.conversation_history = LLMConversationHistory(messages)
        conversation_history = shell_state.conversation_history
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
        shell_state.last_usage_info = usage or {}
    else:
        conversation_history = shell_state.conversation_history
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
    return True


def handle_prompt_loop(
    shell_state, session, profile_manager, agent, max_rounds, session_id
):
    global active_prompt_session
    conversation_history = shell_state.conversation_history
    message_handler = RichMessageHandler()
    console = message_handler.console
    while True:
        try:
            if shell_state.paste_mode:
                user_input = session.prompt("Multiline> ", multiline=True)
                was_paste_mode = True
                shell_state.paste_mode = False
            else:
                user_input = session.prompt(
                    HTML("<inputline>💬 </inputline>"), multiline=False
                )
                was_paste_mode = False
        except EOFError:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except KeyboardInterrupt:
            console.print()
            try:
                confirm = (
                    session.prompt(
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
        shell_state.mem_history.append_string(user_input)
        shell_state.user_input_history.append(user_input)
        conversation_history.add_message({"role": "user", "content": user_input})
        handle_chat(shell_state, profile_manager, agent, max_rounds, session_id)
    # Save conversation history after exiting
    save_conversation_history(conversation_history, session_id)


def handle_chat(shell_state, profile_manager, agent, max_rounds, session_id):
    conversation_history = shell_state.conversation_history
    message_handler = RichMessageHandler()
    console = message_handler.console
    start_time = time.time()
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
        return
    except ProviderError as e:
        message_handler.handle_message(
            {"type": "error", "message": f"Provider error: {e}"}
        )
        return
    except EmptyResponseError as e:
        message_handler.handle_message({"type": "error", "message": f"Error: {e}"})
        return
    except ApiError as e:
        message_handler.handle_message({"type": "error", "message": str(e)})
        return
    shell_state.last_elapsed = time.time() - start_time
    usage = response.get("usage")
    if usage:
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            shell_state.last_usage_info[k] = usage.get(k, 0)
    content = response.get("content")
    if content and (
        len(conversation_history) == 0
        or conversation_history.get_messages()[-1].get("role") != "assistant"
    ):
        conversation_history.add_message({"role": "assistant", "content": content})


def save_conversation_history(conversation_history, session_id):
    from janito.shell.session.manager import get_session_id

    history_dir = os.path.join(os.path.expanduser("~"), ".janito", "chat_history")
    os.makedirs(history_dir, exist_ok=True)
    session_id_to_save = session_id if session_id else get_session_id()
    history_path = os.path.join(history_dir, f"{session_id_to_save}.json")
    conversation_history.to_json_file(history_path)


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
    i18n.set_locale(runtime_config.get("lang", "en"))
    global active_prompt_session
    agent = profile_manager.agent
    message_handler = RichMessageHandler()
    console = message_handler.console
    console.clear()
    shell_state = ShellState()
    shell_state.profile_manager = profile_manager
    user_input_history = UserInputHistory()
    user_input_dicts = user_input_history.load()
    mem_history = shell_state.mem_history
    for item in user_input_dicts:
        if isinstance(item, dict) and "input" in item:
            mem_history.append_string(item["input"])
    shell_state.user_input_history = user_input_history
    if not load_session(shell_state, continue_session, session_id, profile_manager):
        return

    def last_usage_info_ref():
        return shell_state.last_usage_info

    last_elapsed = shell_state.last_elapsed
    print_welcome_message(console, continue_id=session_id if continue_session else None)
    session = setup_prompt_session(
        lambda: shell_state.conversation_history.get_messages(),
        last_usage_info_ref,
        last_elapsed,
        mem_history,
        profile_manager,
        agent,
        lambda: shell_state.conversation_history,
    )
    active_prompt_session = session
    handle_prompt_loop(
        shell_state, session, profile_manager, agent, max_rounds, session_id
    )
