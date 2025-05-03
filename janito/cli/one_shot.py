from janito.agent.conversation_exceptions import (
    MaxRoundsExceededError,
    ProviderError,
    EmptyResponseError,
)
from janito.agent.api_exceptions import ApiError


def run_oneshot_mode(args, profile_manager, runtime_config):
    prompt = getattr(args, "input_arg", None)
    from rich.console import Console
    from janito.agent.rich_message_handler import RichMessageHandler

    console = Console()
    message_handler = RichMessageHandler()
    messages = []
    system_prompt_override = runtime_config.get("system_prompt_template")
    if system_prompt_override:
        if not runtime_config.get("vanilla_mode", False) or getattr(
            args, "system", None
        ):
            messages.append({"role": "system", "content": system_prompt_override})
    elif profile_manager.system_prompt_template and not runtime_config.get(
        "vanilla_mode", False
    ):
        messages.append(
            {"role": "system", "content": profile_manager.system_prompt_template}
        )
    messages.append({"role": "user", "content": prompt})
    import time

    info_start_time = None
    if getattr(args, "info", False):
        info_start_time = time.time()
    try:
        max_rounds = 100
        from janito.agent.conversation_history import ConversationHistory

        result = profile_manager.agent.chat(
            ConversationHistory(messages),
            message_handler=message_handler,
            spinner=True,
            max_rounds=max_rounds,
        )
        if (
            getattr(args, "info", False)
            and info_start_time is not None
            and result is not None
        ):
            usage_info = result.get("usage")
            total_tokens = usage_info.get("total_tokens") if usage_info else None
            prompt_tokens = usage_info.get("prompt_tokens") if usage_info else None
            completion_tokens = (
                usage_info.get("completion_tokens") if usage_info else None
            )
            elapsed = time.time() - info_start_time
            console.print(
                f"[bold green]Total tokens:[/] [yellow]{total_tokens}[/yellow] [bold green]| Input:[/] [cyan]{prompt_tokens}[/cyan] [bold green]| Output:[/] [magenta]{completion_tokens}[/magenta] [bold green]| Elapsed:[/] [yellow]{elapsed:.2f}s[/yellow]",
                style="dim",
            )
    except MaxRoundsExceededError:
        console.print("[red]Max conversation rounds exceeded.[/red]")
    except ProviderError as e:
        console.print(f"[red]Provider error:[/red] {e}")
    except EmptyResponseError as e:
        console.print(f"[red]Error:[/red] {e}")
    except ApiError as e:
        if "maximum context length" in str(e):
            console.print(
                f"[red]Error:[/red] {e}\n[bold yellow]Tip:[/] Try using [green]--max-tokens[/green] with a lower value."
            )
        else:
            console.print(f"[red]API error:[/red] {e}")
    except Exception:
        raise
