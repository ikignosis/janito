from janito.agent.runtime_config import runtime_config


def handle_prompt(console, **kwargs):
    profile_manager = kwargs.get("profile_manager")
    prompt = profile_manager.system_prompt_template if profile_manager else None
    if not prompt and profile_manager:
        prompt = profile_manager.render_prompt()
    console.print(f"[bold magenta]System Prompt:[/bold magenta]\n{prompt}")


def handle_role(console, *args, **kwargs):
    state = kwargs.get("state")
    profile_manager = kwargs.get("profile_manager")
    if not args:
        console.print("[bold red]Usage: /role <new role description>[/bold red]")
        return
    new_role = " ".join(args)
    if profile_manager:
        profile_manager.set_role(new_role)
    # Update system message in conversation
    found = False
    for msg in state["messages"]:
        if msg.get("role") == "system":
            msg["content"] = (
                profile_manager.system_prompt_template if profile_manager else new_role
            )
            found = True
            break
    if not found:
        state["messages"].insert(0, {"role": "system", "content": new_role})
    # Also store the raw role string
    if profile_manager:
        setattr(profile_manager, "role_name", new_role)
    runtime_config.set("role", new_role)
    console.print(f"[bold green]System role updated to:[/bold green] {new_role}")


def handle_profile(console, *args, **kwargs):
    """/profile <new_profile> - Change the interaction profile (e.g., default, technical)"""
    state = kwargs.get("state")
    profile_manager = kwargs.get("profile_manager")
    if not args:
        current = getattr(profile_manager, "interaction_profile", "default")
        console.print(f"[bold green]Current profile:[/bold green] {current}")
        return
    new_profile = args[0]
    if profile_manager:
        profile_manager.set_interaction_profile(new_profile)
    # Update system message in conversation
    found = False
    for msg in state["messages"]:
        if msg.get("role") == "system":
            msg["content"] = (
                profile_manager.system_prompt_template
                if profile_manager
                else msg["content"]
            )
            found = True
            break
    if not found:
        state["messages"].insert(
            0,
            {
                "role": "system",
                "content": (
                    profile_manager.system_prompt_template
                    if profile_manager
                    else new_profile
                ),
            },
        )
    console.print(
        f"[bold green]Interaction profile updated to:[/bold green] {new_profile}"
    )
