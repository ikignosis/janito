    session = PromptSession(
        multiline=True,
        key_bindings=bindings,
        editing_mode=EditingMode.EMACS,
        bottom_toolbar=get_toolbar,
        style=style,
        history=mem_history
    )

    prompt_icon = HTML('<prompt>💬 </prompt>')

    while True:
        try:
            user_input = session.prompt(prompt_icon)
            stripped_input = user_input.strip()

            # Handle commands
            command_result = handle_command(stripped_input, console=console)
            if command_result is not None:
                # For /paste, replace user_input
                if isinstance(command_result, str):
                    user_input = command_result
                    if not user_input:
                        continue
                else:
                    # Command was handled (e.g., /help), skip agent
                    continue

            user_input = user_input.strip()
            if not user_input:
                # Instead of resending last message, treat empty input as 'do it'
                user_input = "do it"
                console.print("[dim]Empty input detected. Interpreting as: 'do it'[/dim]")

            # Save input to history
            history_list.append(user_input)
            try:
                with open(history_file, "w", encoding="utf-8") as f:
                    json.dump(history_list, f, ensure_ascii=False, indent=2)
            except Exception as e:
                console.print(f"[red]Failed to save input history: {e}[/red]")

            messages.append({"role": "user", "content": user_input})

            def on_content(data):
                content = data.get("content", "")
                console.print(Markdown(content))

            try:
                start_time = time.time()
                try:
                    content, usage_info = agent.chat(messages, on_content=on_content)
