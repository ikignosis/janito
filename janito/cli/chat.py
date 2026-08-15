"""
CLI chat execution modes: interactive and single prompt.
"""

import os
from collections.abc import Callable

from .. import __version__
from ..general_config import resolve_api_type
from ..openai_client import RequestCancelled, resolve_runtime_config, send_prompt
from ..shell import InteractiveShell
from ..system_prompt import (  # noqa: F401 (re-exported; tests patch chat_mod.get_system_prompt_with_skills)
    get_system_prompt_with_skills,
)
from ..tooling.path_utils import display_path


def _make_send_prompt_func(
    api_type: str,
    cli_model: str | None = None,
    cli_provider: str | None = None,
    reasoning_level: str | None = None,
):
    """Return a send-prompt callable bound to the resolved API type.

    The returned wrapper accepts the union of the Completions, Responses and
    Anthropic call signatures so the interactive shell can call it identically
    in all modes:

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
      - Anthropic mode: forwards ``previous_messages`` / ``instructions`` to
        ``anthropic_api.send_prompt`` (the native Anthropic SDK) and returns
        the assistant text (the history list is mutated, like Completions).
      - DashScope mode: forwards ``previous_messages`` / ``instructions`` to
        ``dashscope_api.send_prompt`` (the native DashScope SDK) and returns
        the assistant text (the history list is mutated, like Completions).

    Args:
        api_type: The canonical API type: "Responses", "Completions",
            "Anthropic" or "DashScope".
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

    if api_type == "Anthropic":
        # Native Anthropic SDK client (the optional `anthropic` package; the
        # API type is only settable when that package is installed).
        from ..openai_client.anthropic_api import send_prompt as send_anthropic

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
            return send_anthropic(
                prompt,
                verbose=verbose,
                previous_messages=previous_messages,
                instructions=instructions,
                tools=tools,
                thinking=thinking,
                cli_model=cli_model,
                cli_provider=cli_provider,
                reasoning_level=reasoning_level,
            )

        return send

    if api_type == "DashScope":
        # Native DashScope SDK client (the optional `dashscope` package; the
        # API type is only settable when that package is installed).
        from ..dashscope_api import send_prompt as send_dashscope

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
            return send_dashscope(
                prompt,
                verbose=verbose,
                previous_messages=previous_messages,
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


def _make_send_factory(
    cli_api_type: str | None,
    cli_model: str | None,
    cli_provider: str | None,
    cli_reasoning_level: str | None,
) -> Callable[[str | None], Callable]:
    """Return a factory that builds the send function for a provider.

    The interactive shell stores the returned factory as ``send_factory`` and
    ``/provider`` calls it with the new provider, so a provider switch takes
    effect in real time.  For the target provider the factory re-resolves:

      - **model**: ``--model`` only applies to the provider it was given for
        (the session's startup provider).  After a switch the new provider's
        configured model, else its built-in default, is used (matching the
        toolbar display updated by ``/provider``).
      - **API type**: ``--api-type``, then the model-scoped configured
        value for that provider/model, then the built-in default.

    Args:
        cli_api_type: API type passed via ``--api-type`` (may be None).
        cli_model: Model passed via ``--model`` (may be None).
        cli_provider: Provider passed via ``--provider`` (may be None).
        cli_reasoning_level: Reasoning depth passed via ``--reasoning-level``
            (may be None).

    Returns:
        A callable ``factory(provider) -> send_prompt_func``.
    """

    def send_factory(provider: str | None) -> Callable:
        from janito.config_loaders import load_model_from_config
        from janito.provider_accessors import get_default_model_from_provider

        # --model applies to the startup provider only; a switched-to provider
        # gets its own effective model (configured, else built-in default).
        if (provider or "").lower() == (cli_provider or "").lower():
            model = cli_model
        else:
            model = load_model_from_config(provider) or get_default_model_from_provider(
                provider
            )
        return _make_send_prompt_func(
            resolve_api_type(cli_api_type, provider, model),
            cli_model=model,
            cli_provider=provider,
            reasoning_level=cli_reasoning_level,
        )

    return send_factory


def print_version_banner(console=None):
    """Print a banner with the version and the current working directory."""
    from rich.console import Console

    if console is None:
        console = Console()
    console.print(
        f"Janito [cyan]{__version__}[/cyan] - Working at "
        f"[magenta]{display_path(os.getcwd())}[/magenta]"
    )


def _print_full_privileges_warning(args) -> None:
    """Print a warning banner when running with full privileges."""
    if getattr(args, "full_privileges", False):
        from rich.console import Console

        print_version_banner()
        Console().print(
            "WARNING: Running with full privileges, consider using -r, -w, -x",
            style="yellow",
        )


def _enable_requested_toolsets(args) -> None:
    """Enable Gmail/OneDrive toolsets when requested via CLI flags."""
    from .session_setup import SessionSetup

    SessionSetup(gmail=args.gmail, onedrive=args.onedrive).enable_toolsets()
    if args.gmail:
        print("\u2713 Gmail tools enabled")

    if args.onedrive:
        print("\u2713 OneDrive tools enabled")


def _resolve_system_prompt(args) -> tuple[str | None, bool]:
    """Return ``(effective_system_prompt, no_tools)`` for the enabled modes."""
    from .session_setup import SessionSetup

    setup = SessionSetup(
        system_prompt=args.system_prompt,
        no_system_prompt=args.no_system_prompt,
        gmail=args.gmail,
        onedrive=args.onedrive,
    )
    return setup.effective_system_prompt(), setup.no_tools


def _print_tool_summary(args) -> None:
    """Report the total number of active and skipped tools."""
    from ..tooling.tools_registry import get_all_tools
    from ..tools import get_skipped_tools

    active_tools = get_all_tools()
    skipped_tools = get_skipped_tools()
    print(f"\u2713 {len(active_tools)} tool(s) active, {len(skipped_tools)} skipped")
    if skipped_tools and args.verbose:
        for tool_name, reason in skipped_tools.items():
            print(f"    - {tool_name}: {reason}")


def run_interactive_chat(args):
    """Run the interactive chat session.

    Args:
        args: Parsed command line arguments
    """
    _print_full_privileges_warning(args)
    _enable_requested_toolsets(args)

    # Check if any skills are installed
    from ..tooling.skills_provider import get_skills_provider

    skills = get_skills_provider().list_skills()
    if skills:
        print(f"\u2713 {len(skills)} skill(s) available")

    _print_tool_summary(args)

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
    print(
        "Starting interactive chat session. Type '/exit' or CTRL-D to end the session"
    )

    # Choose system prompt based on enabled modes
    effective_system_prompt, no_tools = _resolve_system_prompt(args)

    shell = InteractiveShell(
        model=model,
        no_history=args.no_history,
        provider=cli_provider,
    )
    # Factory to (re)build the send function per provider: ``/provider`` calls
    # it with the new provider so the switch takes effect in real time
    # (provider, model and API type are re-resolved, see _make_send_factory).
    shell.send_factory = _make_send_factory(
        cli_api_type, cli_model, cli_provider, cli_reasoning_level
    )
    shell.initialize_history(system_prompt=effective_system_prompt)
    shell.run(
        send_prompt_func=shell.send_factory(cli_provider),
        verbose=args.verbose,
        no_tools=no_tools,
        thinking=args.thinking,
    )


def _build_single_prompt_context(args):
    """Build ``(messages_history, tools_to_use)`` for a single prompt run."""
    from .session_setup import SessionSetup

    setup = SessionSetup(
        system_prompt=args.system_prompt,
        no_system_prompt=args.no_system_prompt,
        gmail=args.gmail,
        onedrive=args.onedrive,
    )
    return setup.messages_context(), setup.tools_arg()


def run_single_prompt(args):
    """Run a single prompt.

    Args:
        args: Parsed command line arguments
    """
    import sys

    _print_full_privileges_warning(args)
    _enable_requested_toolsets(args)

    prompt = args.prompt

    if not prompt:
        print("Error: Empty prompt provided.", file=sys.stderr)
        sys.exit(1)

    # Initialize messages history (with or without system prompt based on -Z or -S flag)
    messages_history, tools_to_use = _build_single_prompt_context(args)

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
