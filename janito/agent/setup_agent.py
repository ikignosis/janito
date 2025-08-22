import importlib.resources
import re
import os
import sys
import time
import warnings
import threading
from pathlib import Path
from jinja2 import Template
from pathlib import Path
from queue import Queue
from rich import print as rich_print
from janito.tools import get_local_tools_adapter
from janito.llm.agent import LLMAgent

from janito.platform_discovery import PlatformDiscovery
from janito.tools.tool_base import ToolPermissions
from janito.tools.permissions import get_global_allowed_permissions


def _load_template_content(profile, templates_dir):
    """
    Loads the template content for the given profile from the specified directory or package resources.
    If the profile template is not found in the default locations, tries to load from the user profiles directory ~/.janito/profiles.

    Spaces in the profile name are converted to underscores to align with the file-naming convention (e.g. "Developer with Python Tools" ➜ "Developer_with_Python_Tools" (matches: system_prompt_template_Developer_with_Python_Tools.txt.j2)).
    """
    sanitized_profile = re.sub(r"\s+", "_", profile.strip())
    template_filename = f"system_prompt_template_{sanitized_profile}.txt.j2"

    return _find_template_file(template_filename, templates_dir)


def _find_template_file(template_filename, templates_dir):
    """Find and load template file from various locations."""
    template_path = templates_dir / template_filename

    # 1) Check local templates directory
    if template_path.exists():
        with open(template_path, "r", encoding="utf-8") as file:
            return file.read(), template_path

    # 2) Try package resources fallback
    try:
        with importlib.resources.files("janito.agent.templates.profiles").joinpath(
            template_filename
        ).open("r", encoding="utf-8") as file:
            return file.read(), template_path
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        pass

    # 3) Finally, look in the user profiles directory (~/.janito/profiles)
    user_profiles_dir = Path(os.path.expanduser("~/.janito/profiles"))
    user_template_path = user_profiles_dir / template_filename
    if user_template_path.exists():
        with open(user_template_path, "r", encoding="utf-8") as file:
            return file.read(), user_template_path

    # If nothing matched, list available profiles and raise an informative error
    from janito.cli.cli_commands.list_profiles import (
        _gather_default_profiles,
        _gather_user_profiles,
    )

    default_profiles = _gather_default_profiles()
    user_profiles = _gather_user_profiles()

    available_profiles = []
    if default_profiles:
        available_profiles.extend([(p, "default") for p in default_profiles])
    if user_profiles:
        available_profiles.extend([(p, "user") for p in user_profiles])

    # Normalize the input profile for better matching suggestions
    normalized_input = re.sub(r"\s+", " ", profile.strip().lower())

    if available_profiles:
        profile_list = "\n".join(
            [f"  - {name} ({source})" for name, source in available_profiles]
        )

        # Find close matches
        close_matches = []
        for name, source in available_profiles:
            normalized_name = name.lower()
            if (
                normalized_input in normalized_name
                or normalized_name in normalized_input
            ):
                close_matches.append(name)

        suggestion = ""
        if close_matches:
            suggestion = f"\nDid you mean: {', '.join(close_matches)}?"

        error_msg = f"[janito] Could not find profile '{profile}'. Available profiles:\n{profile_list}{suggestion}"
    else:
        error_msg = (
            f"[janito] Could not find profile '{profile}'. No profiles available."
        )

    raise FileNotFoundError(error_msg)


def _prepare_template_context(role, profile, allowed_permissions, args=None):
    """
    Prepares the context dictionary for Jinja2 template rendering.
    """
    context = {}
    context["role"] = role or "developer"
    context["profile"] = profile
    if allowed_permissions is None:
        allowed_permissions = get_global_allowed_permissions()
    # Convert ToolPermissions -> string like "rwx"
    if isinstance(allowed_permissions, ToolPermissions):
        perm_str = ""
        if allowed_permissions.read:
            perm_str += "r"
        if allowed_permissions.write:
            perm_str += "w"
        if allowed_permissions.execute:
            perm_str += "x"
        allowed_permissions = perm_str or None
    context["allowed_permissions"] = allowed_permissions

    # Add emoji flag for system prompt
    context["emoji_enabled"] = (
        getattr(args, "emoji", False) if "args" in locals() else False
    )
    # Inject platform info if execute permission is present
    if allowed_permissions and "x" in allowed_permissions:
        pd = PlatformDiscovery()
        context["platform"] = pd.get_platform_name()
        context["python_version"] = pd.get_python_version()
        context["shell_info"] = pd.detect_shell()

    # Add allowed sites for market analyst profile
    if profile == "market-analyst":
        from janito.tools.url_whitelist import get_url_whitelist_manager

        whitelist_manager = get_url_whitelist_manager()
        allowed_sites = whitelist_manager.get_allowed_sites()
        context["allowed_sites"] = allowed_sites

        # Add market data sources documentation
        if not allowed_sites:
            context["allowed_sites_info"] = (
                "No whitelist restrictions - all sites allowed"
            )
        else:
            context["allowed_sites_info"] = f"Restricted to: {', '.join(allowed_sites)}"

    # Add emoji flag for system prompt
    context["emoji_enabled"] = (
        getattr(args, "emoji", False) if "args" in locals() else False
    )

    # Add current date/time with timezone using standard library
    from datetime import datetime, timezone
    import time

    # Get local time with timezone info
    local_time = datetime.now()

    # Get timezone offset
    if time.daylight:
        offset = time.altzone
    else:
        offset = time.timezone

    # Format offset as +HHMM or -HHMM
    offset_hours = -offset // 3600
    offset_minutes = abs(offset) % 3600 // 60
    offset_str = f"{offset_hours:+03d}{offset_minutes:02d}"

    # Get timezone name
    tz_name = time.tzname[time.daylight and time.daylight or 0]

    context["current_datetime"] = local_time.strftime(
        f"%Y-%m-%d %H:%M:%S {tz_name}{offset_str}"
    )
    context["timezone"] = f"{tz_name} (UTC{offset_str})"

    return context


def _create_agent(
    provider_instance,
    tools_provider,
    role,
    system_prompt,
    input_queue,
    output_queue,
    verbose_agent,
    context,
    template_path,
    profile,
):
    """
    Creates and returns an LLMAgent instance with the provided parameters.
    """
    agent = LLMAgent(
        provider_instance,
        tools_provider,
        agent_name=role or "developer",
        system_prompt=system_prompt,
        input_queue=input_queue,
        output_queue=output_queue,
        verbose_agent=verbose_agent,
    )
    agent.template_vars["role"] = context["role"]
    agent.template_vars["profile"] = profile
    agent.system_prompt_template = str(template_path)
    agent._template_vars = context.copy()
    agent._original_template_vars = context.copy()
    return agent


def setup_agent(
    provider_instance,
    llm_driver_config,
    role=None,
    templates_dir=None,
    zero_mode=False,
    input_queue=None,
    output_queue=None,
    verbose_tools=False,
    verbose_agent=False,
    allowed_permissions=None,
    profile=None,
    profile_system_prompt=None,
    no_tools_mode=False,
):
    """
    Creates an agent. A system prompt is rendered from a template only when a profile is specified.
    """
    if no_tools_mode or zero_mode:
        tools_provider = None
    else:
        tools_provider = get_local_tools_adapter()
        tools_provider.set_verbose_tools(verbose_tools)

    # If zero_mode is enabled or no profile is given we skip the system prompt.
    if zero_mode or (profile is None and profile_system_prompt is None):
        agent = LLMAgent(
            provider_instance,
            tools_provider,
            agent_name=role or "developer",
            system_prompt=None,
            input_queue=input_queue,
            output_queue=output_queue,
            verbose_agent=verbose_agent,
        )
        if role:
            agent.template_vars["role"] = role
        return agent

    # If profile_system_prompt is set, use it directly
    if profile_system_prompt is not None:
        agent = LLMAgent(
            provider_instance,
            tools_provider,
            agent_name=role or "developer",
            system_prompt=profile_system_prompt,
            input_queue=input_queue,
            output_queue=output_queue,
            verbose_agent=verbose_agent,
        )
        agent.template_vars["role"] = role or "developer"
        agent.template_vars["profile"] = None
        agent.template_vars["profile_system_prompt"] = profile_system_prompt
        return agent

    # Normal flow (profile-specific system prompt)
    if templates_dir is None:
        templates_dir = Path(__file__).parent / "templates" / "profiles"
    template_content, template_path = _load_template_content(profile, templates_dir)

    template = Template(template_content)
    context = _prepare_template_context(
        role, profile, allowed_permissions, locals().get("args")
    )

    # Debug output if requested
    debug_flag = False
    try:
        debug_flag = hasattr(sys, "argv") and (
            "--debug" in sys.argv or "--verbose" in sys.argv or "-v" in sys.argv
        )
    except Exception:
        pass
    if debug_flag:
        rich_print(
            f"[bold magenta][DEBUG][/bold magenta] Rendering system prompt template '[cyan]{template_path.name}[/cyan]' with allowed_permissions: [yellow]{context.get('allowed_permissions')}[/yellow]"
        )
        rich_print(
            f"[bold magenta][DEBUG][/bold magenta] Template context: [green]{context}[/green]"
        )
    start_render = time.time()
    rendered_prompt = template.render(**context)
    end_render = time.time()
    # Merge multiple empty lines into a single empty line
    rendered_prompt = re.sub(r"\n{3,}", "\n\n", rendered_prompt)

    return _create_agent(
        provider_instance,
        tools_provider,
        role,
        rendered_prompt,
        input_queue,
        output_queue,
        verbose_agent,
        context,
        template_path,
        profile,
    )


def create_configured_agent(
    *,
    provider_instance=None,
    llm_driver_config=None,
    role=None,
    verbose_tools=False,
    verbose_agent=False,
    templates_dir=None,
    zero_mode=False,
    allowed_permissions=None,
    profile=None,
    profile_system_prompt=None,
    no_tools_mode=False,
):
    """
    Normalizes agent setup for all CLI modes.

    Args:
        provider_instance: Provider instance for the agent
        llm_driver_config: LLM driver configuration
        role: Optional role string
        verbose_tools: Optional, default False
        verbose_agent: Optional, default False
        templates_dir: Optional
        zero_mode: Optional, default False

    Returns:
        Configured agent instance
    """
    input_queue = None
    output_queue = None
    driver = None
    if hasattr(provider_instance, "create_driver"):
        driver = provider_instance.create_driver()
        # Ensure no tools are passed to the driver when --no-tools flag is active
        if no_tools_mode:
            driver.tools_adapter = None
        driver.start()  # Ensure the driver background thread is started
        input_queue = getattr(driver, "input_queue", None)
        output_queue = getattr(driver, "output_queue", None)

    agent = setup_agent(
        provider_instance=provider_instance,
        llm_driver_config=llm_driver_config,
        role=role,
        templates_dir=templates_dir,
        zero_mode=zero_mode,
        input_queue=input_queue,
        output_queue=output_queue,
        verbose_tools=verbose_tools,
        verbose_agent=verbose_agent,
        allowed_permissions=allowed_permissions,
        profile=profile,
        profile_system_prompt=profile_system_prompt,
        no_tools_mode=no_tools_mode,
    )
    if driver is not None:
        agent.driver = driver  # Attach driver to agent for thread management
    return agent
