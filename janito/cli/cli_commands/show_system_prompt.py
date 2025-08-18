"""
CLI Command: Show the resolved system prompt for the main agent (single-shot mode)

Supports --profile to select a profile-specific system prompt template.
"""

from janito.cli.core.runner import prepare_llm_driver_config
from janito.platform_discovery import PlatformDiscovery
from pathlib import Path
from jinja2 import Template
import importlib.resources
import importlib.resources as resources
import re


def _compute_permission_string(args):
    from janito.tools.tool_base import ToolPermissions

    read = getattr(args, "read", False)
    write = getattr(args, "write", False)
    execute = getattr(args, "exec", False)
    allowed = ToolPermissions(read=read, write=write, execute=execute)
    perm_str = ""
    if allowed.read:
        perm_str += "r"
    if allowed.write:
        perm_str += "w"
    if allowed.execute:
        perm_str += "x"
    return perm_str or None


def _prepare_context(args, agent_role, allowed_permissions):
    context = {}
    context["role"] = agent_role or "developer"
    context["profile"] = getattr(args, "profile", None)
    context["allowed_permissions"] = allowed_permissions
    context["emoji_enabled"] = getattr(args, "emoji", False)
    if allowed_permissions and "x" in allowed_permissions:
        pd = PlatformDiscovery()
        context["platform"] = pd.get_platform_name()
        context["python_version"] = pd.get_python_version()
        context["shell_info"] = pd.detect_shell()
    return context


def _load_template(profile, templates_dir):
    if profile:
        sanitized_profile = re.sub(r"\\s+", "_", profile.strip())
        template_filename = f"system_prompt_template_{sanitized_profile}.txt.j2"
        template_path = templates_dir / template_filename
    else:
        return None, None
    template_content = None
    if template_path and template_path.exists():
        with open(template_path, "r", encoding="utf-8") as file:
            template_content = file.read()
    else:
        try:
            with importlib.resources.files("janito.agent.templates.profiles").joinpath(
                template_filename
            ).open("r", encoding="utf-8") as file:
                template_content = file.read()
        except (FileNotFoundError, ModuleNotFoundError, AttributeError):
            # Also check user profiles directory
            from pathlib import Path
            import os

            user_profiles_dir = Path(os.path.expanduser("~/.janito/profiles"))
            user_template_path = user_profiles_dir / template_filename
            if user_template_path.exists():
                with open(user_template_path, "r", encoding="utf-8") as file:
                    template_content = file.read()
            else:
                template_content = None
            return template_filename, template_content
    return template_filename, template_content


def _print_debug_info(debug_flag, template_filename, allowed_permissions, context):
    if debug_flag:
        from rich import print as rich_print

        rich_print(
            f"[bold magenta][DEBUG][/bold magenta] Rendering system prompt template '[cyan]{template_filename}[/cyan]' with allowed_permissions: [yellow]{allowed_permissions}[/yellow]"
        )
        rich_print(
            f"[bold magenta][DEBUG][/bold magenta] Template context: [green]{context}[/green]"
        )


def handle_show_system_prompt(args):
    from janito.cli.main_cli import MODIFIER_KEYS

    modifiers = {
        k: getattr(args, k) for k in MODIFIER_KEYS if getattr(args, k, None) is not None
    }
    provider, llm_driver_config, agent_role = prepare_llm_driver_config(args, modifiers)
    if provider is None or llm_driver_config is None:
        print("Error: Could not resolve provider or LLM driver config.")
        return

    allowed_permissions = _compute_permission_string(args)
    context = _prepare_context(args, agent_role, allowed_permissions)

    # Debug flag detection
    import sys

    debug_flag = False
    try:
        debug_flag = hasattr(sys, "argv") and (
            "--debug" in sys.argv or "--verbose" in sys.argv or "-v" in sys.argv
        )
    except Exception:
        pass

    templates_dir = (
        Path(__file__).parent.parent.parent / "agent" / "templates" / "profiles"
    )
    profile = getattr(args, "profile", None)

    # Handle --market flag mapping to Market Analyst profile
    if profile is None and getattr(args, "market", False):
        profile = "Market Analyst"

    # Handle --developer flag mapping to Developer With Python Tools profile
    if profile is None and getattr(args, "developer", False):
        profile = "Developer With Python Tools"

    if not profile:
        print(
            "[janito] No profile specified. The main agent runs without a system prompt template.\n"
            "Use --profile PROFILE to view a profile-specific system prompt."
        )
        return

    template_filename, template_content = _load_template(profile, templates_dir)
    _print_debug_info(debug_flag, template_filename, allowed_permissions, context)

    if not template_content:
        # Try to load directly from package resources as fallback
        try:
            template_content = (
                resources.files("janito.agent.templates.profiles")
                .joinpath(
                    f"system_prompt_template_{profile.lower().replace(' ', '_')}.txt.j2"
                )
                .read_text(encoding="utf-8")
            )
        except (FileNotFoundError, ModuleNotFoundError, AttributeError):
            print(
                f"[janito] Could not find profile '{profile}'. This may be a configuration issue."
            )
            return

    template = Template(template_content)
    system_prompt = template.render(**context)
    system_prompt = re.sub(r"\n{3,}", "\n\n", system_prompt)

    # Use the actual profile name for display, not the resolved value
    display_profile = profile or "main"
    print(f"\n--- System Prompt (resolved, profile: {display_profile}) ---\n")
    print(system_prompt)
    print("\n-------------------------------\n")
    if agent_role:
        print(f"[Role: {agent_role}]")
