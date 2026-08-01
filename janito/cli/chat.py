"""
CLI chat execution modes: interactive and single prompt.
"""

from functools import partial

from ..openai_client import RequestCancelled, resolve_runtime_config, send_prompt
from ..shell import InteractiveShell
from ..system_prompt import get_system_prompt_with_skills
from ..tools.gmail import GMAIL_SYSTEM_PROMPT
from ..tools.onedrive import ONEDRIVE_SYSTEM_PROMPT


def run_interactive_chat(args):
    """Run the interactive chat session.

    Args:
        args: Parsed command line arguments
    """
    if getattr(args, "full_privileges", False):
        from rich.console import Console

        Console().print(
            "WARNING: Running with full privileges, consider using -r, -w, -x",
            style="yellow",
        )

    # Set up Gmail mode if requested
    if args.gmail:
        from ..tooling.tools_registry import add_toolset

        add_toolset("gmail")
        print("✓ Gmail tools enabled")

    # Set up OneDrive mode if requested
    if args.onedrive:
        from ..tooling.tools_registry import add_toolset

        add_toolset("onedrive")
        print("✓ OneDrive tools enabled")

    # Check if any skills are installed
    from ..tooling.skills_provider import get_skills_provider

    skills = get_skills_provider().list_skills()
    if skills:
        print(f"✓ {len(skills)} skill(s) available")

    # Report the total number of active and skipped tools
    from ..tooling.tools_registry import get_all_tools
    from ..tools import get_skipped_tools

    active_tools = get_all_tools()
    skipped_tools = get_skipped_tools()
    print(f"✓ {len(active_tools)} tool(s) active, {len(skipped_tools)} skipped")
    if skipped_tools and args.verbose:
        for tool_name, reason in skipped_tools.items():
            print(f"    - {tool_name}: {reason}")

    # Resolve the model for display (and bind CLI model/provider so every
    # prompt uses the same configuration without environment variables).
    cli_model = getattr(args, "model", None)
    cli_provider = getattr(args, "provider", None)
    try:
        _, _, model = resolve_runtime_config(cli_model, cli_provider)
    except ValueError:
        model = cli_model or "(not configured)"
    send_prompt_func = partial(
        send_prompt, cli_model=cli_model, cli_provider=cli_provider
    )
    print(
        "Starting interactive chat session. Type '/exit' or CTRL-D to end the session"
    )

    # Choose system prompt based on enabled modes
    if args.system_prompt:
        effective_system_prompt = args.system_prompt
        no_tools = True
    elif args.no_system_prompt:
        effective_system_prompt = None
        no_tools = True
    elif args.onedrive:
        effective_system_prompt = ONEDRIVE_SYSTEM_PROMPT
        no_tools = False
    elif args.gmail:
        effective_system_prompt = GMAIL_SYSTEM_PROMPT
        no_tools = False
    else:
        # Use system prompt with skills advertisement
        effective_system_prompt = get_system_prompt_with_skills()
        no_tools = False

    shell = InteractiveShell(
        model=model,
        no_history=args.no_history,
        provider=cli_provider,
    )
    shell.initialize_history(system_prompt=effective_system_prompt)
    shell.run(
        send_prompt_func=send_prompt_func,
        verbose=args.verbose,
        no_tools=no_tools,
        thinking=args.thinking,
    )


def run_single_prompt(args):
    """Run a single prompt.

    Args:
        args: Parsed command line arguments
    """
    import sys

    if getattr(args, "full_privileges", False):
        from rich.console import Console

        Console().print(
            "WARNING: Running with full privileges, consider using -r, -w, -x",
            style="yellow",
        )

    # Set up Gmail mode if requested
    if args.gmail:
        from ..tooling.tools_registry import add_toolset

        add_toolset("gmail")
        print("✓ Gmail tools enabled")

    # Set up OneDrive mode if requested
    if args.onedrive:
        from ..tooling.tools_registry import add_toolset

        add_toolset("onedrive")
        print("✓ OneDrive tools enabled")

    prompt = args.prompt

    if not prompt:
        print("Error: Empty prompt provided.", file=sys.stderr)
        sys.exit(1)

    # Initialize messages history (with or without system prompt based on -Z or -S flag)
    if args.system_prompt:
        messages_history = [{"role": "system", "content": args.system_prompt}]
        tools_to_use = []
    elif args.no_system_prompt:
        messages_history = []
        tools_to_use = []
    else:
        # Choose system prompt based on enabled modes
        if args.onedrive:
            effective_system_prompt = ONEDRIVE_SYSTEM_PROMPT
        elif args.gmail:
            effective_system_prompt = GMAIL_SYSTEM_PROMPT
        else:
            # Use system prompt with skills advertisement
            effective_system_prompt = get_system_prompt_with_skills()
        messages_history = [{"role": "system", "content": effective_system_prompt}]
        tools_to_use = None

    try:
        send_prompt(
            prompt,
            verbose=args.verbose,
            previous_messages=messages_history,
            tools=tools_to_use,
            thinking=args.thinking,
            cli_model=getattr(args, "model", None),
            cli_provider=getattr(args, "provider", None),
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except RequestCancelled:
        # Enter was pressed while waiting for the API response.
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
