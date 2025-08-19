"""Handlers for set-type CLI commands (provider, model, api keys, etc)."""

from janito.provider_config import set_config_provider
from janito.config import config as global_config
from janito.provider_registry import ProviderRegistry
from janito.cli.cli_commands.set_api_key import handle_set_api_key


def handle_api_key_set(args):
    if getattr(args, "set_api_key", None):
        handle_set_api_key(args)
        return True
    return False


def handle_set(args, config_mgr=None):
    set_arg = getattr(args, "set", None)
    if not set_arg:
        return False
    try:
        if not _validate_set_arg_format(set_arg):
            return True
        key, value = _parse_set_arg(set_arg)
        key = key.replace("-", "_")
        return _dispatch_set_key(key, value)
    except Exception as e:
        print(f"Error parsing --set value: {e}")
        return True


def _validate_set_arg_format(set_arg):
    if "=" not in set_arg:
        print("Error: --set requires KEY=VALUE (e.g., --set provider=provider_name).")
        return False
    return True


def _parse_set_arg(set_arg):
    key, value = set_arg.split("=", 1)
    return key.strip(), value.strip()


def _dispatch_set_key(key, value):
    if key == "provider":
        return _handle_set_config_provider(value)
    if key == "model":
        return _handle_set_global_model(value)
    if key == "max_tokens":
        return _handle_set_max_tokens(value)
    if key == "base_url":
        return _handle_set_base_url(value)
    if key in ["azure_deployment_name", "azure-deployment-name"]:
        global_config.file_set("azure_deployment_name", value)
        print(f"Azure deployment name set to '{value}'.")
        return True
    if key == "tool_permissions":
        from janito.tools.permissions_parse import parse_permissions_string
        from janito.tools.permissions import set_global_allowed_permissions

        perms = parse_permissions_string(value)
        global_config.file_set("tool_permissions", value)
        set_global_allowed_permissions(perms)
        print(f"Tool permissions set to '{value}' (parsed: {perms})")
        return True
    if key == "disabled_tools":
        from janito.tools.disabled_tools import set_disabled_tools

        set_disabled_tools(value)
        global_config.file_set("disabled_tools", value)
        print(f"Disabled tools set to '{value}'")
        return True
    if key == "allowed_sites":
        from janito.tools.url_whitelist import get_url_whitelist_manager

        sites = [site.strip() for site in value.split(",") if site.strip()]
        whitelist_manager = get_url_whitelist_manager()
        whitelist_manager.set_allowed_sites(sites)
        global_config.file_set("allowed_sites", value)
        print(f"Allowed sites set to: {', '.join(sites)}")
        return True
    print(
        f"Error: Unknown config key '{key}'. Supported: provider, model, max_tokens, base_url, azure_deployment_name, tool_permissions, disabled_tools, allowed_sites"
    )
    return True


def _handle_set_max_tokens(value):
    try:
        ival = int(value)
    except Exception:
        print("Error: max_tokens must be set to an integer value.")
        return True
    global_config.file_set("max_tokens", ival)
    print(f"Top-level max_tokens set to {ival}.")
    return True


def _handle_set_base_url(value):
    global_config.file_set("base_url", value)
    print(f"Top-level base_url set to {value}.")
    return True


def set_provider(value):
    """Set the current provider.

    Args:
        value (str): The provider name to set

    Raises:
        ValueError: If the provider is not supported
    """
    try:
        supported = ProviderRegistry().get_provider(value)
    except Exception:
        raise ValueError(
            f"Provider '{value}' is not supported. Run '--list-providers' to see the supported list."
        )
    from janito.provider_config import set_config_provider

    set_config_provider(value)


def _handle_set_config_provider(value):
    try:
        set_provider(value)
    except ValueError as e:
        print(f"Error: {str(e)}")
        return True
    print(f"Provider set to '{value}'.")
    return True


def _handle_set_global_model(value):
    # Try to validate model choice (against current provider if possible)
    provider_name = global_config.get("provider")
    if provider_name:
        try:
            provider_cls = ProviderRegistry().get_provider(provider_name)
            provider_instance = provider_cls()
            model_info = provider_instance.get_model_info(value)
            if not model_info:
                print(
                    f"Error: Model '{value}' is not defined for provider '{provider_name}'. Run '-p {provider_name} -l' to see models."
                )
                return True
        except Exception:
            print(
                f"Warning: Could not validate model for provider '{provider_name}'. Setting anyway."
            )
    else:
        print(
            "Warning: No provider set. Model will be set globally, but may not be valid for any provider."
        )
    global_config.file_set("model", value)
    print(f"Global default model set to '{value}'.")
    return True
