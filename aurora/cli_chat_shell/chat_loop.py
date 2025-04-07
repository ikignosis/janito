from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit.history import InMemoryHistory
from .session_manager import load_last_summary, load_last_conversation, load_input_history
from .ui import print_summary, print_welcome, get_toolbar_func, get_prompt_session
from .commands import handle_command


def start_chat_shell(agent, continue_session=False):
    console = Console()

    # Show last saved conversation summary
    data = load_last_summary()
    print_summary(console, data, continue_session)

    # Load input history
    history_list = load_input_history()
    mem_history = InMemoryHistory()
    for item in history_list:
        mem_history.append_string(item)

    # Initialize chat state
state = {
    'messages': messages,
    'mem_history': mem_history,
    'last_usage_info': last_usage_info,
    'last_elapsed': last_elapsed,
}
    messages = []
    last_usage_info = None
    last_elapsed = None

    # Restore conversation if requested
    if continue_session:
        msgs, prompts, usage = load_last_conversation()
        messages = msgs
        last_usage_info = usage
        mem_history = InMemoryHistory()
        for item in prompts:
            mem_history.append_string(item)
        console.print('[bold green]Restored last saved conversation.[/bold green]')

    # Add system prompt if needed
    if agent.system_prompt and not any(m.get('role') == 'system' for m in messages):
        messages.insert(0, {"role": "system", "content": agent.system_prompt})

    print_welcome(console)

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
        get_toolbar_func(get_messages, get_usage, get_elapsed, model_name=model_name),
        mem_history
    )

    prompt_icon = "\U0001F4AC "  # 💬

    # Main chat loop
    while True:
        try:
            user_input = session.prompt(prompt_icon)
        except EOFError:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except KeyboardInterrupt:
            console.print()  # Move to next line
            confirm = input("Do you really want to exit? (y/n): ").strip().lower()
            if confirm == 'y':
                console.print("[bold red]Exiting...[/bold red]")
                break
            else:
                continue

        if user_input.strip().startswith('/'):
            result = handle_command(user_input.strip(), console, agent=agent, messages=messages, mem_history=mem_history, state=state)
            if result == 'exit':
                break
            continue

        if not user_input.strip():
            user_input = "do it"

        mem_history.append_string(user_input)
        messages.append({"role": "user", "content": user_input})

        start_time = None
        import time
        start_time = time.time()
        try:
            response = agent.chat(messages)
        except KeyboardInterrupt:
            console.print("[bold yellow]Request interrupted. Returning to prompt.[/bold yellow]")
            continue
        last_elapsed = time.time() - start_time

        content = response.get('content')
        usage = response.get('usage')
        last_usage_info = usage

        if content:
            console.print(Markdown(content))
            messages.append({"role": "assistant", "content": content})

        # Save conversation and input history
        from .session_manager import save_conversation, save_input_history
        prompts = [h for h in mem_history.get_strings()]
        save_conversation(messages, prompts, last_usage_info)
        save_input_history(prompts)
