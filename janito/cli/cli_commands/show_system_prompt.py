"""
CLI Command: Show the resolved system prompt for the main agent (single-shot mode)

Supports --profile to select a profile-specific system prompt template.
"""

from janito.cli.core.runner import prepare_llm_driver_config
from janito.agent.system_prompt import SystemPromptTemplateManager
from janito.tooling.tool_base import ToolPermissions
from pathlib import Path


def handle_show_system_prompt(args):
    from janito.cli.main_cli import MODIFIER_KEYS

    modifiers = {
        k: getattr(args, k) for k in MODIFIER_KEYS if getattr(args, k, None) is not None
    }
    provider, llm_driver_config, agent_role = prepare_llm_driver_config(args, modifiers)
    if provider is None or llm_driver_config is None:
        print("Error: Could not resolve provider or LLM driver config.")
        return

    # Compute allowed permissions
    read = getattr(args, "read", False)
    write = getattr(args, "write", False)
    execute = getattr(args, "exec", False)
    allowed_permissions = ToolPermissions(read=read, write=write, execute=execute)

    # Determine profile
    profile = getattr(args, "profile", None)

    # Handle --market flag mapping to Market Analyst profile
    if profile is None and getattr(args, "market", False):
        profile = "Market Analyst"

    # Handle --developer flag mapping to Developer profile
    if profile is None and getattr(args, "developer", False):
        profile = "Developer"

    if not profile:
        print(
            "[janito] No profile specified. The main agent runs without a system prompt template.\n"
            "Use --profile PROFILE to view a profile-specific system prompt."
        )
        return

    # Create template manager and render the profile
    templates_dir = (
        Path(__file__).parent.parent.parent / "agent" / "templates" / "profiles"
    )
    template_manager = SystemPromptTemplateManager(templates_dir=templates_dir)

    try:
        system_prompt, context, template_path = template_manager.render_profile(
            profile=profile,
            role=agent_role,
            allowed_permissions=allowed_permissions,
        )
    except FileNotFoundError as e:
        print(str(e))
        return

    # Use the actual profile name for display, not the resolved value
    display_profile = profile or "main"
    print(f"\n--- System Prompt (resolved, profile: {display_profile}) ---")
    print(system_prompt)
    print("-------------------------------")
    if agent_role:
        print(f"[Role: {agent_role}]")
