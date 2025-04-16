from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit.history import InMemoryHistory
from .session_manager import load_last_conversation, load_input_history
from .ui import print_welcome, get_toolbar_func, get_prompt_session
from janito import __version__
from .commands import handle_command
from janito.agent.config import effective_config
from janito.agent.runtime_config import runtime_config
from janito.agent.conversation import EmptyResponseError, ProviderError


def start_chat_shell(agent, continue_session=False, max_rounds=50):
    console = Console()

    # Load input history
    history_list = load_input_history()
    mem_history = InMemoryHistory()
    for item in history_list:
        mem_history.append_string(item)

        # Initialize chat state variables
    messages = []
    last_usage_info = None
    last_elapsed = None

    state = {
        'messages': messages,
        'mem_history': mem_history,
        'history_list': history_list,
        'last_usage_info': last_usage_info,
        'last_elapsed': last_elapsed,
    }

    # Restore conversation if requested
    if continue_session:
        msgs, prompts, usage = load_last_conversation()
        messages = msgs
        last_usage_info = usage
        mem_history = InMemoryHistory()
        for item in prompts:
            mem_history.append_string(item)
        # update state dict with restored data

        state['messages'] = messages
        state['last_usage_info'] = last_usage_info
        state['mem_history'] = mem_history
        console.print('[bold green]Restored last saved conversation.[/bold green]')

    # Add system prompt if needed
    if agent.system_prompt and not any(m.get('role') == 'system' for m in messages):
        messages.insert(0, {"role": "system", "content": agent.system_prompt})

    print_welcome(console, version=__version__)

    # Toolbar references
    def get_messages():
        return messages

    def get_usage():
        return last_usage_info

    def get_elapsed():
        return last_elapsed

    # Try to get model name from agent
    model_name = getattr(agent, 'model', None)

    session = get_prompt_session(
        get_toolbar_func(
            get_messages, get_usage, get_elapsed, model_name=model_name,
            role_ref=lambda: ("*using custom system prompt*" if (runtime_config.get('system_prompt') or runtime_config.get('system_prompt_file')) else (runtime_config.get('role') or effective_config.get('role')))
        ),
        mem_history
    )


    # Main chat loop
    while True:
        # max_rounds is now available for use in the chat loop

        try:
            if state.get('paste_mode'):
                console.print('')
                user_input = session.prompt('Multiline> ', multiline=True)
                was_paste_mode = True
                state['paste_mode'] = False
            else:
                from prompt_toolkit.formatted_text import HTML
                user_input = session.prompt(HTML('<prompt>💬 </prompt>'), multiline=False)
                was_paste_mode = False
        except EOFError:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except KeyboardInterrupt:
            console.print()  # Move to next line
            try:
                confirm = input("Do you really want to exit? (y/n): ").strip().lower()
            except KeyboardInterrupt:
                console.print("\n[bold red]Exiting...[/bold red]")
                break
            if confirm == 'y':
                console.print("[bold red]Exiting...[/bold red]")
                break
            else:
                continue

        if not was_paste_mode and user_input.strip().startswith('/'):
            result = handle_command(user_input.strip(), console, agent=agent, messages=messages, mem_history=mem_history, state=state)
            if result == 'exit':
                break
            continue

        if not user_input.strip():
            continue

        mem_history.append_string(user_input)
        messages.append({"role": "user", "content": user_input})

        start_time = None
        import time
        start_time = time.time()

        # Define streaming content handler
        def on_content(chunk):
            content_piece = chunk.get('content')
            if content_piece:
                console.print(Markdown(content_piece))

        try:
            response = agent.chat(messages, on_content=on_content, spinner=True, max_rounds=max_rounds)
        except KeyboardInterrupt:
            console.print("[bold yellow]Request interrupted. Returning to prompt.[/bold yellow]")
            continue
        except ProviderError as e:
            console.print(f"[bold red]Provider error:[/bold red] {e}")
            continue
        except EmptyResponseError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            continue
        last_elapsed = time.time() - start_time

        usage = response.get('usage')
        last_usage_info = usage

        # Save conversation and input history
        from .session_manager import save_conversation, save_input_history
        prompts = [h for h in mem_history.get_strings()]
        save_conversation(messages, prompts, last_usage_info)
        save_input_history(prompts)
