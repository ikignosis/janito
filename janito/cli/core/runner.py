"""Handles LLM driver config preparation and execution modes."""

from janito.llm.driver_config import LLMDriverConfig
from janito.provider_config import get_config_provider
from janito.cli.core.model_guesser import (
    guess_provider_from_model as _guess_provider_from_model,
)
from janito.cli.verbose_output import print_verbose_info


def _choose_provider(args):
    provider = getattr(args, "provider", None)
    if provider is None:
        provider = get_config_provider()
        if provider and getattr(args, "verbose", False):
            print_verbose_info(
                "Default provider", provider, style="magenta", align_content=True
            )
        elif provider is None:
            # Try to guess provider based on model name if -m is provided
            model = getattr(args, "model", None)
            if model:
                guessed_provider = _guess_provider_from_model(model)
                if guessed_provider:
                    if getattr(args, "verbose", False):
                        print_verbose_info(
                            "Guessed provider",
                            guessed_provider,
                            style="magenta",
                            align_content=True,
                        )
                    return guessed_provider

            print(
                "Error: No provider selected and no provider found in config. Please set a provider using '-p PROVIDER', '--set provider=name', or configure a provider."
            )
            return None
    return provider


def _populate_driver_config_data(args, modifiers, provider, model):
    from janito.provider_config import get_effective_setting

    CONFIG_LOOKUP_KEYS = ("max_tokens", "base_url")
    driver_config_data = {"model": model}
    if getattr(args, "verbose_api", None) is not None:
        driver_config_data["verbose_api"] = args.verbose_api

    # Add reasoning_effort from --effort CLI argument
    if getattr(args, "effort", None) is not None:
        driver_config_data["reasoning_effort"] = args.effort
    for field in LLMDriverConfig.__dataclass_fields__:
        if field in CONFIG_LOOKUP_KEYS:
            if field in modifiers and modifiers[field] is not None:
                driver_config_data[field] = modifiers[field]
            else:
                value = get_effective_setting(provider, model, field)
                if value is not None:
                    driver_config_data[field] = value
        elif field in modifiers and field != "model":
            driver_config_data[field] = modifiers[field]
    return driver_config_data


def prepare_llm_driver_config(args, modifiers):
    """Prepare the LLMDriverConfig instance based on CLI *args* and *modifiers*.

    This helper additionally validates that the chosen ``--model`` (or the
    resolved model coming from config precedence) is actually available for the
    selected provider.  If the combination is invalid an error is printed and
    ``None`` is returned for the config so that the caller can abort execution
    gracefully.
    """
    provider = _choose_provider(args)
    if provider is None:
        return None, None, None
    from janito.provider_config import get_effective_model

    model = getattr(args, "model", None)
    if not model:
        model = get_effective_model(provider)

    # Validate that the chosen model is supported by the selected provider
    if model:
        from janito.provider_registry import ProviderRegistry

        provider_instance = None
        provider_instance = ProviderRegistry().get_instance(provider)
        if provider_instance is None:
            return provider, None, None
        try:
            if not provider_instance.is_model_available(model):
                print(
                    f"Error: Model '{model}' is not available for provider '{provider}'."
                )
                # Optionally, print available models if possible
                if hasattr(provider_instance, "get_model_info"):
                    available_models = [
                        m["name"]
                        for m in provider_instance.get_model_info().values()
                        if isinstance(m, dict) and "name" in m
                    ]
                    print(f"Available models: {', '.join(available_models)}")
                return provider, None, None
        except Exception as e:
            print(f"Error validating model for provider '{provider}': {e}")
            return provider, None, None
    driver_config_data = _populate_driver_config_data(args, modifiers, provider, model)
    llm_driver_config = LLMDriverConfig(**driver_config_data)
    if getattr(llm_driver_config, "verbose_api", None):
        pass

    agent_role = modifiers.get("profile") or "developer"
    return provider, llm_driver_config, agent_role


def handle_runner(
    args,
    provider,
    llm_driver_config,
    agent_role,
    verbose_tools=False,
):
    """
    Main runner for CLI execution. If exec_enabled is False, disables execution/run tools.
    """
    zero_mode = getattr(args, "zero", False)
    from janito.provider_registry import ProviderRegistry

    # Patch: disable execution/run tools if not enabled
    import janito.tools
    from janito.tools.tool_base import ToolPermissions

    read = getattr(args, "read", False)
    write = getattr(args, "write", False)
    execute = getattr(args, "exec", False)
    from janito.tools.permissions import set_global_allowed_permissions
    from janito.tools.tool_base import ToolPermissions

    allowed_permissions = ToolPermissions(read=read, write=write, execute=execute)
    set_global_allowed_permissions(allowed_permissions)
    # Store the default permissions for later restoration (e.g., on /restart)
    from janito.tools.permissions import set_default_allowed_permissions

    set_default_allowed_permissions(allowed_permissions)

    # Load disabled tools from config
    from janito.tools.disabled_tools import load_disabled_tools_from_config

    load_disabled_tools_from_config()

    unrestricted = getattr(args, "unrestricted", False)
    adapter = janito.tools.get_local_tools_adapter(
        workdir=getattr(args, "workdir", None)
    )
    if unrestricted:
        # Patch: disable path security enforcement for this adapter instance
        setattr(adapter, "unrestricted_paths", True)

        # Also disable URL whitelist restrictions in unrestricted mode
        from janito.tools.url_whitelist import get_url_whitelist_manager

        whitelist_manager = get_url_whitelist_manager()
        whitelist_manager.set_unrestricted_mode(True)

    # Print allowed permissions in verbose mode
    if getattr(args, "verbose", False):
        print_verbose_info(
            "Allowed Tool Permissions",
            f"read={read}, write={write}, execute={execute}",
            style="yellow",
        )

    provider_instance = ProviderRegistry().get_instance(provider, llm_driver_config)
    if provider_instance is None:
        return
    mode = get_prompt_mode(args)
    if getattr(args, "verbose", False):
        print_verbose_info(
            "Active LLMDriverConfig (after provider)", llm_driver_config, style="green"
        )
        print_verbose_info("Agent role", agent_role, style="green")

    # Skip chat mode for list commands - handle them directly
    from janito.cli.core.getters import GETTER_KEYS

    skip_chat_mode = False
    if args is not None:
        for key in GETTER_KEYS:
            if getattr(args, key, False):
                skip_chat_mode = True
                break

    if skip_chat_mode:
        # Handle list commands directly without prompt
        from janito.cli.core.getters import handle_getter

        handle_getter(args)
    elif mode == "single_shot":
        from janito.cli.single_shot_mode.handler import (
            PromptHandler as SingleShotPromptHandler,
        )

        # DEBUG: Print exec_enabled propagation at runner

        handler = SingleShotPromptHandler(
            args,
            provider_instance,
            llm_driver_config,
            role=agent_role,
            allowed_permissions=allowed_permissions,
        )
        handler.handle()
    else:
        from janito.cli.chat_mode.session import ChatSession
        from rich.console import Console

        console = Console()
        session = ChatSession(
            console,
            provider_instance,
            llm_driver_config,
            role=agent_role,
            args=args,
            verbose_tools=verbose_tools,
            verbose_agent=getattr(args, "verbose_agent", False),
            allowed_permissions=allowed_permissions,
        )
        session.run()


def get_prompt_mode(args):
    return "single_shot" if getattr(args, "user_prompt", None) else "chat_mode"
