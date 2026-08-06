"""
CLI chat execution modes: interactive and single prompt.
"""

import os

from .. import __version__
from ..general_config import resolve_api_type
from ..openai_client import RequestCancelled, resolve_runtime_config, send_prompt
from ..shell import InteractiveShell
from ..system_prompt import get_system_prompt_with_skills
from ..tooling.path_utils import display_path
from ..tools.gmail import GMAIL_SYSTEM_PROMPT
from ..tools.onedrive import ONEDRIVE_SYSTEM_PROMPT


def _make_send_prompt_func(
    api_type: str,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    reasoning_level: str | None = None,
):
    """Return a send-prompt callable bound to the resolved API type.

    The returned wrapper accepts the union of the Completions and Responses
    call signatures so the interactive shell can call it identically in both
    modes:

      - Completions mode: forwards ``previous_messages`` to
        ``completions_api.send_prompt`` and returns the assistant text (the
        history list is mutated as before).
      - Responses mode: forwards ``previous_response_id`` / ``instructions``
        (server-side providers) or ``previous_items`` (stateless providers,
        e.g. DeepSeek) to ``conversations_api.send_prompt`` and returns a
        ``ConversationResult``. For server-side providers the conversation
        lives on the server, so ``previous_messages`` is ignored (the
        history is no longer stored/updated on the client side); stateless
        providers track the history in ``previous_items`` instead.

    Args:
        api_type: "Responses" or "Completions".
        cli_model: Model passed via ``--model``.
        cli_provider: Provider passed via ``--provider``.
        reasoning_level: Reasoning depth passed via ``--reasoning-level``.
    """
    if api_type == "Responses":
        from ..openai_client.conversations_api import send_prompt as send_responses

        def send(
            prompt,
            verbose=False,
            previous_messages=None,
            previous_response_id=None,
            previous_items=None,
            instructions=None,
            tools=None,
            thinking=False,
        ):
            return send_responses(
                prompt,
                verbose=verbose,
                previous_response_id=previous_response_id,
                previous_items=previous_items,
                instructions=instructions,
                tools=tools,
                thinking=thinking,
                cli_model=cli_model,
                cli_provider=cli_provider,
                reasoning_level=reasoning_level,
            )

        return send

    def send(
        prompt,
        verbose=False,
        previous_messages=None,
        previous_response_id=None,
        previous_items=None,
        instructions=None,
        tools=None,
        thinking=False,
    ):
        return send_prompt(
            prompt,
            verbose=verbose,
            previous_messages=previous_messages,
            tools=tools,
            thinking=thinking,
            cli_model=cli_model,
            cli_provider=cli_provider,
            reasoning_level=reasoning_level,
        )

    return send


def print_version_banner(console=None):
    """Print a banner with the version and the current working directory."""
    from rich.console import Console

    if console is None:
        console = Console()
    console.print(
        f"Janito [cyan]{__version__}[/cyan] - Working at "
        f"[magenta]{display_path(os.getcwd())}[/magenta]"
    )


def run_interactive_chat(args):
    """Run the interactive chat session.

    Args:
        args: Parsed command line arguments
    """
    if getattr(args, "full_privileges", False):
        from rich.console import Console

        print_version_banner()
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
    cli_reasoning_level = getattr(args, "reasoning_level", None)
    cli_api_type = getattr(args, "api_type", None)
    try:
        _, _, model = resolve_runtime_config(cli_model, cli_provider)
    except ValueError:
        model = cli_model or "(not configured)"
    # Select the API type for the provider: --api-type, then the provider's
    # configured api-type (--set api-type=...), then the provider's built-in
    # default (the first entry of its supported_api_types list).
    api_type = resolve_api_type(cli_api_type, cli_provider)
    send_prompt_func = _make_send_prompt_func(
        api_type,
        cli_model=cli_model,
        cli_provider=cli_provider,
        reasoning_level=cli_reasoning_level,
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

        print_version_banner()
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
        # Select the API type for the provider: --api-type, then the
        # provider's configured api-type, then its built-in default.
        send_prompt_func = _make_send_prompt_func(
            resolve_api_type(
                getattr(args, "api_type", None),
                getattr(args, "provider", None),
            ),
            cli_model=getattr(args, "model", None),
            cli_provider=getattr(args, "provider", None),
            reasoning_level=getattr(args, "reasoning_level", None),
        )
        # In Responses mode the system prompt is sent as `instructions` on the
        # first turn (extracted from the seeded history); in Completions mode
        # the same value is carried inside `previous_messages`.
        instructions = None
        if messages_history and messages_history[0].get("role") == "system":
            instructions = messages_history[0].get("content")
        send_prompt_func(
            prompt,
            verbose=args.verbose,
            previous_messages=messages_history,
            instructions=instructions,
            tools=tools_to_use,
            thinking=args.thinking,
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except RequestCancelled:
        # Enter was pressed while waiting for the API response.
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
